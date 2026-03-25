from __future__ import annotations

import pytest

from v10.core.config import load_config


def test_load_config_rejects_unknown_yaml_keys(tmp_path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        "\n".join(
            [
                "engine:",
                "  symbol: BTCUSDT",
                "  bad_engine_key: 1",
                "strategy:",
                "  name: v8_apex",
                "  bad_strategy_key: 2",
                "risk:",
                "  max_total_exposure: 1.0",
                "unknown_top_level: 3",
                "",
            ]
        )
    )

    with pytest.raises(ValueError) as exc:
        load_config(path)

    message = str(exc.value)
    assert "unknown_top_level" in message
    assert "engine.bad_engine_key" in message
    assert "strategy.bad_strategy_key" in message
