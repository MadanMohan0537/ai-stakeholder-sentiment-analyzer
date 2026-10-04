from pathlib import Path
import app


def test_ui_analyze_review_and_export():
    assert app.build_app().config["dependencies"]
    stats, note, table, trend, topics, raw, context = app.run(
        app.SAMPLE, "Offline demo"
    )
    assert len(table) == 6
    saved, files = app.save(raw, context)
    assert len(files) == 3 and all(Path(p).is_file() for p in files)
