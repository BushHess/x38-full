"""Volatility-Conditioned Block Bootstrap (VCBB).

Standard block bootstrap (uniform) destroys 84% of BTC's volatility clustering
at block boundaries. VCBB conditions next-block selection on realized volatility
at the previous block's end via K-nearest-neighbor lookup, restoring cross-block
volatility continuity while remaining non-parametric.

Usage
-----
    from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

    cr, hr, lr, vol, tb = make_ratios(cl, hi, lo, vo, tb_raw)
    vcbb = precompute_vcbb(cr, blksz=60, ctx=90)
    c, h, l, v, t = gen_path_vcbb(cr, hr, lr, vol, tb, n_trans, blksz, p0, rng,
                                   vcbb=vcbb, K=50)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


# ═══════════════════════════════════════════════════════════════════════════════
# Data types
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class VCBBState:
    """Precomputed state for vol-conditioned block bootstrap.

    Attributes
    ----------
    rvol : np.ndarray, shape (N,)
        Realized vol at each transition index.  rvol[i] = std(log_r[i-ctx+1:i+1]).
        Entries with i < ctx-1 are NaN (insufficient history).
    sorted_idx : np.ndarray, shape (M,)
        Valid block start positions sorted by their rvol value.
        M = number of valid starts where rvol is not NaN.
    sorted_vol : np.ndarray, shape (M,)
        rvol[sorted_idx] — vol values in sorted order for binary search.
    blksz : int
        Block size used.
    ctx : int
        Context window used.
    """

    rvol: np.ndarray
    sorted_idx: np.ndarray
    sorted_vol: np.ndarray
    blksz: int
    ctx: int


# ═══════════════════════════════════════════════════════════════════════════════
# Ratio computation (drop-in replacements for copy-pasted versions)
# ═══════════════════════════════════════════════════════════════════════════════


def make_ratios(cl, hi, lo, vo, tb):
    """Convert OHLCV arrays to multiplicative ratios (5-channel, Family A).

    Returns (cr, hr, lr, vol, tb) where:
        cr[i] = close[i+1] / close[i]
        hr[i] = high[i+1]  / close[i]
        lr[i] = low[i+1]   / close[i]
        vol, tb are shifted copies (absolute values).
    """
    pc = cl[:-1]
    return cl[1:] / pc, hi[1:] / pc, lo[1:] / pc, vo[1:].copy(), tb[1:].copy()




# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _build_idx(starts, blksz, n_trans):
    """Build flat index array from block starts."""
    idx = np.concatenate([np.arange(s, s + blksz) for s in starts])[:n_trans]
    return idx


def _build_path_5ch(cr, hr, lr, vol, tb, idx, p0):
    """Reconstruct 5-channel price path from index array."""
    c = np.empty(len(idx) + 1, dtype=np.float64)
    c[0] = p0
    c[1:] = p0 * np.cumprod(cr[idx])

    h = np.empty_like(c)
    l = np.empty_like(c)
    v = np.empty_like(c)
    t = np.empty_like(c)

    h[0] = p0 * 1.002
    l[0] = p0 * 0.998
    v[0] = vol[idx[0]]
    t[0] = tb[idx[0]]

    h[1:] = c[:-1] * hr[idx]
    l[1:] = c[:-1] * lr[idx]
    v[1:] = vol[idx]
    t[1:] = tb[idx]

    np.maximum(h, c, out=h)
    np.minimum(l, c, out=l)

    return c, h, l, v, t



def _compute_rvol(cr, ctx):
    """Compute rolling realized vol from close return ratios.

    rvol[i] = std(log(cr[i-ctx+1 : i+1]))

    Parameters
    ----------
    cr : np.ndarray, shape (N,)
        Close-to-close return ratios.
    ctx : int
        Context window (number of returns).

    Returns
    -------
    rvol : np.ndarray, shape (N,)
        Realized vol.  rvol[i] = NaN for i < ctx-1.
    """
    log_r = np.log(cr)
    n = len(log_r)
    rvol = np.full(n, np.nan, dtype=np.float64)

    if n < ctx:
        return rvol

    # Vectorized rolling std via cumulative sums
    cs = np.cumsum(log_r)
    cs2 = np.cumsum(log_r ** 2)

    # For window [i-ctx+1 : i+1]:
    #   sum   = cs[i] - cs[i-ctx]  (with cs[-1] = 0 convention)
    #   sum_sq = cs2[i] - cs2[i-ctx]
    # Prepend 0 for the subtraction
    cs_pad = np.concatenate([[0.0], cs])
    cs2_pad = np.concatenate([[0.0], cs2])

    for i in range(ctx - 1, n):
        s = cs_pad[i + 1] - cs_pad[i - ctx + 1]
        s2 = cs2_pad[i + 1] - cs2_pad[i - ctx + 1]
        var = s2 / ctx - (s / ctx) ** 2
        rvol[i] = math.sqrt(max(var, 0.0))

    return rvol


def _knn_select(target_vol, sorted_vol, sorted_idx, K, rng):
    """Select one block start from K nearest neighbors in vol space.

    Uses binary search to find insertion point, then expands outward
    to collect K nearest neighbors.

    Parameters
    ----------
    target_vol : float
        Target realized vol to match.
    sorted_vol : np.ndarray, shape (M,)
        Vol values sorted ascending.
    sorted_idx : np.ndarray, shape (M,)
        Corresponding original indices.
    K : int
        Number of nearest neighbors.
    rng : np.random.Generator
        Random generator for selection.

    Returns
    -------
    int
        Selected block start position.
    """
    M = len(sorted_vol)
    K = min(K, M)

    # Binary search for insertion point
    pos = np.searchsorted(sorted_vol, target_vol)

    # Expand window to collect K nearest neighbors
    lo = max(0, pos - K)
    hi = min(M, pos + K)

    # Find the K closest within [lo, hi)
    candidates = np.arange(lo, hi)
    dists = np.abs(sorted_vol[candidates] - target_vol)
    if len(candidates) > K:
        # Partial sort to find K smallest distances
        kth = np.argpartition(dists, K)[:K]
        candidates = candidates[kth]

    # Uniform selection from K nearest
    chosen = rng.integers(0, len(candidates))
    return int(sorted_idx[candidates[chosen]])


def _select_blocks_vcbb(n_blk, mx, blksz, vcbb, rng, K, cr=None):
    """VCBB block selection: first block uniform, rest vol-conditioned.

    Conditions the next block on the realized vol computed from the
    SYNTHETIC path's accumulated returns (not from the original data's
    position).  This propagates vol state through the entire path,
    restoring long-range vol dependence across multiple block boundaries.

    Parameters
    ----------
    n_blk : int
        Number of blocks to select.
    mx : int
        Max valid block start index (len(cr) - blksz).
    blksz : int
        Block size.
    vcbb : VCBBState
        Precomputed vol state.
    rng : np.random.Generator
        Random generator.
    K : int
        Number of nearest neighbors.
    cr : np.ndarray or None
        Close return ratios (needed to compute synthetic path vol).
        If None, falls back to original-data vol lookup.

    Returns
    -------
    starts : np.ndarray, shape (n_blk,)
        Selected block start indices.
    """
    starts = np.empty(n_blk, dtype=np.int64)
    ctx = vcbb.ctx

    # First block: uniform
    starts[0] = rng.integers(0, mx + 1)

    if cr is None:
        # Fallback: original-data vol lookup (v1 behavior)
        for k in range(1, n_blk):
            prev_end = starts[k - 1] + blksz - 1
            if prev_end < len(vcbb.rvol) and not np.isnan(vcbb.rvol[prev_end]):
                target_vol = vcbb.rvol[prev_end]
                starts[k] = _knn_select(
                    target_vol, vcbb.sorted_vol, vcbb.sorted_idx, K, rng
                )
            else:
                starts[k] = rng.integers(0, mx + 1)
        return starts

    # Build log returns incrementally from the synthetic path
    log_cr = np.log(cr)

    # Collect log returns of synthetic path as we go
    synth_log_r = np.empty(n_blk * blksz, dtype=np.float64)
    n_synth = 0

    # First block's returns
    s0 = starts[0]
    synth_log_r[:blksz] = log_cr[s0 : s0 + blksz]
    n_synth = blksz

    for k in range(1, n_blk):
        # Compute target vol from the synthetic path's last ctx returns
        if n_synth >= ctx:
            window = synth_log_r[n_synth - ctx : n_synth]
            m = window.mean()
            var = (window * window).mean() - m * m
            target_vol = math.sqrt(max(var, 0.0))
        elif n_synth > 1:
            window = synth_log_r[:n_synth]
            m = window.mean()
            var = (window * window).mean() - m * m
            target_vol = math.sqrt(max(var, 0.0))
        else:
            # Not enough data — uniform fallback
            starts[k] = rng.integers(0, mx + 1)
            s = starts[k]
            end = min(s + blksz, len(log_cr))
            chunk = end - s
            synth_log_r[n_synth : n_synth + chunk] = log_cr[s : end]
            n_synth += chunk
            continue

        starts[k] = _knn_select(
            target_vol, vcbb.sorted_vol, vcbb.sorted_idx, K, rng
        )

        # Append this block's returns to synthetic path
        s = starts[k]
        end = min(s + blksz, len(log_cr))
        chunk = end - s
        synth_log_r[n_synth : n_synth + chunk] = log_cr[s : end]
        n_synth += chunk

    return starts


# ═══════════════════════════════════════════════════════════════════════════════
# Public API — VCBB (vol-conditioned block bootstrap)
# ═══════════════════════════════════════════════════════════════════════════════


def precompute_vcbb(cr, blksz, ctx=90):
    """Precompute vol lookup structures for VCBB.

    Call once per dataset.  O(N log N) from the sort.

    Parameters
    ----------
    cr : np.ndarray, shape (N,)
        Close return ratios from make_ratios().
    blksz : int
        Block size in bars.
    ctx : int
        Context window for realized vol computation.

    Returns
    -------
    VCBBState
        Precomputed state for use with gen_path_vcbb().
    """
    rvol = _compute_rvol(cr, ctx)

    mx = len(cr) - blksz
    if mx < 0:
        mx = 0

    # Valid block starts: positions [0, mx] where rvol is defined
    valid_starts = np.arange(mx + 1)
    valid_mask = ~np.isnan(rvol[valid_starts])
    valid_starts = valid_starts[valid_mask]
    valid_vol = rvol[valid_starts]

    # Sort by vol for binary search
    order = np.argsort(valid_vol)
    sorted_idx = valid_starts[order]
    sorted_vol = valid_vol[order]

    return VCBBState(
        rvol=rvol,
        sorted_idx=sorted_idx,
        sorted_vol=sorted_vol,
        blksz=blksz,
        ctx=ctx,
    )


def gen_path_vcbb(cr, hr, lr, vol, tb, n_trans, blksz, p0, rng,
                  vcbb, K=50):
    """Generate one bootstrap path via vol-conditioned block resampling (Family A).

    Parameters
    ----------
    cr, hr, lr, vol, tb : np.ndarray
        Ratio arrays from make_ratios().
    n_trans : int
        Number of transitions (bars - 1).
    blksz : int
        Block size.
    p0 : float
        Initial price.
    rng : np.random.Generator
        Random generator.
    vcbb : VCBBState
        Precomputed vol state from precompute_vcbb().
    K : int
        Number of nearest neighbors for vol matching.

    Returns
    -------
    tuple of (c, h, l, v, t)
        Reconstructed price arrays.
    """
    n_blk = math.ceil(n_trans / blksz)
    mx = len(cr) - blksz
    if mx <= 0:
        idx = np.arange(min(n_trans, len(cr)))
    else:
        starts = _select_blocks_vcbb(n_blk, mx, blksz, vcbb, rng, K, cr=cr)
        idx = _build_idx(starts, blksz, n_trans)
    return _build_path_5ch(cr, hr, lr, vol, tb, idx, p0)


