from sermon_archive.schemas import IndexOverview


def test_index_overview_preserves_actionable_sermon_coverage_details():
    overview = IndexOverview.model_validate(
        {
            "source_sermon_count": 2,
            "indexed_sermon_count": 1,
            "missing_sermon_count": 1,
            "stale_sermon_count": 1,
            "missing_sermons": [
                {
                    "sermon_id": 12,
                    "title": "Missing sermon",
                    "speaker_name": "A. Speaker",
                    "preached_on": "2026-01-04",
                    "source_updated_at": "2026-01-05T12:00:00Z",
                }
            ],
            "stale_sermons": [
                {
                    "sermon_id": 13,
                    "title": "Stale sermon",
                    "source_updated_at": "2026-01-06T12:00:00Z",
                    "indexed_at": "2026-01-05T12:00:00Z",
                }
            ],
        }
    )

    assert overview.missing_sermons[0].title == "Missing sermon"
    assert overview.stale_sermons[0].sermon_id == 13
    assert overview.missing_sermon_count == len(overview.missing_sermons)
