from pathlib import Path
import app


def test_ui_analyze_review_and_export():
    endpoints = {event["api_name"] for event in app.build_app().config["dependencies"]}
    assert {"check_local_ai", "test_local_ai"} <= endpoints
    stats, note, table, trend, topics, raw, context = app.run(
        app.SAMPLE, "Offline demo"
    )
    assert len(table) == 6
    saved, files = app.save(raw, context)
    assert len(files) == 3 and all(Path(p).is_file() for p in files)
