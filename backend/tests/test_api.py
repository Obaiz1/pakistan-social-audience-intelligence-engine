import pytest

from audienceiq.api import schemas

ROUTES = ["/api/v1/analytics/overview", "/api/v1/analytics/content", "/api/v1/analytics/campaigns",
          "/api/v1/audience/clusters", "/api/v1/audience/evaluation", "/api/v1/comments", "/api/v1/anomalies",
          "/api/v1/recommendations", "/api/v1/posts", "/api/v1/data/quality", "/api/v1/methodology"]


def test_health_contract(api_client):
    r = api_client.get("/api/v1/health")
    assert r.status_code == 200
    h = schemas.Health(**r.json())
    assert h.status == "ok" and h.datasets == 1 and h.writes_enabled
    assert "key" not in r.text.lower() or "api_key" not in r.text.lower()


def test_datasets_contract(api_client):
    body = api_client.get("/api/v1/datasets").json()
    lst = schemas.DatasetList(**body)
    d = lst.datasets[0]
    assert d.mode == "synthetic" and "SYNTHETIC DEMO" in d.disclaimer and d.post_count == 240
    assert d.sources[0].source_type == "synthetic_generator"


@pytest.mark.parametrize("route", ROUTES)
def test_every_route_returns_meta_envelope(api_client, route):
    r = api_client.get(route)
    assert r.status_code == 200, r.text
    m = schemas.Meta(**r.json()["meta"])
    assert m.mode == "synthetic" and "NOT REAL" in m.disclaimer and m.generated_at


def test_unknown_dataset_and_bad_filters(api_client):
    assert api_client.get("/api/v1/analytics/overview?dataset_id=nope").status_code == 404
    assert api_client.get("/api/v1/posts?platform=MySpace").status_code == 422
    assert api_client.get("/api/v1/posts?date_from=2026-02-01&date_to=2026-01-01").status_code == 422
    assert api_client.get("/api/v1/posts?page_size=1000").status_code == 422
    assert api_client.get("/api/v1/posts?sort=__class__").status_code == 422
    assert api_client.get("/api/v1/audience/clusters/999").status_code == 404
    assert api_client.get("/api/v1/anomalies/none").status_code == 404


def test_posts_pagination_filter_and_detail(api_client):
    page = api_client.get("/api/v1/posts?platform=TikTok&page_size=5&sort=views&order=desc").json()
    assert page["page"]["page_size"] == 5 and all(r["platform"] == "TikTok" for r in page["rows"])
    views = [r["views"] for r in page["rows"]]
    assert views == sorted(views, reverse=True)
    detail = api_client.get(f"/api/v1/posts/{page['rows'][0]['post_id']}").json()
    assert detail["post"]["post_id"] == page["rows"][0]["post_id"] and isinstance(detail["comments"], list)


def test_clusters_and_detail(api_client):
    body = api_client.get("/api/v1/audience/clusters").json()
    assert body["run"]["algorithm"] in {"kmeans", "hdbscan"} and body["clusters"]
    c = next(c for c in body["clusters"] if c["cluster_id"] != -1)
    schemas.ClusterProfile(**c)
    assert sum(x["filtered_size"] for x in body["clusters"]) == body["comments_in_view"]
    d = api_client.get(f"/api/v1/audience/clusters/{c['cluster_id']}").json()
    assert d["cluster"]["cluster_id"] == c["cluster_id"] and "platform" in d["breakdowns"]
    assert d["comments"] and d["comments"][0]["comment_text"]


def test_filtered_cluster_counts_shrink(api_client):
    full = api_client.get("/api/v1/audience/clusters").json()["comments_in_view"]
    part = api_client.get("/api/v1/audience/clusters?platform=Facebook").json()["comments_in_view"]
    assert 0 < part < full


def test_anomalies_and_recommendations_contracts(api_client):
    an = api_client.get("/api/v1/anomalies").json()
    for row in an["rows"]:
        schemas.AnomalyFlag(**row)
    if an["rows"]:
        detail = api_client.get(f"/api/v1/anomalies/{an['rows'][0]['flag_id']}").json()
        assert detail["cohort"]["size"] >= 20
    recs = api_client.get("/api/v1/recommendations").json()["recommendations"]
    assert recs, "the small synthetic bundle should still support at least one card"
    for r in recs:
        schemas.Recommendation(**r)
        assert r["linked_evidence"] and r["test_plan"] and r["limitations"]


def test_comments_privacy_note_and_filters(api_client):
    body = api_client.get("/api/v1/comments?language=urdu&page_size=5").json()
    assert body["permission"]["text_visible"] and all(r["language_type"] == "urdu" for r in body["rows"])
    assert "not a confirmed purchase" in " ".join(body["meta"]["assumptions"])


@pytest.mark.parametrize("fmt,ctype", [("csv", "text/csv"), ("xlsx", "spreadsheetml"), ("pdf", "application/pdf")])
def test_exports(api_client, fmt, ctype):
    r = api_client.get(f"/api/v1/reports/export?format={fmt}&section=posts")
    assert r.status_code == 200 and ctype in r.headers["content-type"] and len(r.content) > 500
    if fmt == "csv":
        assert "SYNTHETIC DEMO" in r.content.decode("utf-8-sig").splitlines()[1]


def test_import_preview_and_confirm_local(api_client):
    posts = "post_id,brand,platform,content_type,likes,comments_count,views,published_at\n" + "".join(
        f"P{i},Brand Z,tiktok,video,{50 + i * 3},{5 + i},{1000 + 37 * i},2026-09-{1 + i % 28:02d}T10:00:00Z\n" for i in range(40))
    texts = ["Price kya hai?", "delivery kitne din?", "beautiful ❤️", "XL size hai?", "discount milega?", "قیمت کیا ہے؟"]
    comments = "post_id,comment_text\n" + "".join(f"P{i % 40},{texts[i % len(texts)]} {i}\n" for i in range(120))
    prev = api_client.post("/api/v1/imports/preview", json={"posts_csv": posts, "comments_csv": comments}).json()
    assert prev["ready"] and prev["posts"]["mapping"]["likes"] == "likes"
    att = {"source_description": "Unit-test export", "collected_at": "2026-11-01", "permission_confirmed": True,
           "data_kind": "synthetic"}
    r = api_client.post("/api/v1/imports/confirm", json={"posts_csv": posts, "comments_csv": comments, "name": "Unit import",
                                                         "attestation": att})
    assert r.status_code == 200, r.text
    ds_id = r.json()["dataset_id"]
    lst = api_client.get("/api/v1/datasets").json()["datasets"]
    assert any(d["dataset_id"] == ds_id and d["mode"] == "imported" for d in lst)
    assert api_client.get(f"/api/v1/audience/clusters?dataset_id={ds_id}").status_code == 200
    assert api_client.delete(f"/api/v1/datasets/{ds_id}").status_code == 200


def test_hosted_mode_is_read_only_but_preview_works(hosted_client):
    assert hosted_client.get("/api/v1/health").json()["writes_enabled"] is False
    r = hosted_client.post("/api/v1/imports/confirm", json={})
    assert r.status_code == 403 and "read-only" in r.json()["detail"]
    assert hosted_client.post("/api/v1/datasets/demo", json={}).status_code == 403
    ok = hosted_client.post("/api/v1/imports/preview", json={"posts_csv": "post_id,brand\n1,a\n"})
    assert ok.status_code == 422                                   # validation error, not a write refusal


def test_cross_site_write_refused(api_client):
    r = api_client.post("/api/v1/imports/preview", json={"posts_csv": "a\n1\n"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_import_confirm_requires_permission(api_client):
    att = {"source_description": "x export", "collected_at": "2026-11-01", "permission_confirmed": False, "data_kind": "observed"}
    r = api_client.post("/api/v1/imports/confirm", json={"posts_csv": "a\n1\n", "comments_csv": "b\n1\n", "name": "abc",
                                                         "attestation": att})
    assert r.status_code == 422
