"""`app/perms.py` 的用例：token 的权限面、密钥在哪种事件下可见、OIDC、action 的钉法。"""
from __future__ import annotations

from app import perms as P


def _b(name: str) -> dict:
    return P.blast_radius(next(g for g in P.GRANTS if g.name.startswith(name)))


def test_the_permissive_default_can_rewrite_the_workflow_itself() -> None:
    b = _b("不写 permissions:（宽松默认）")
    assert b["write_code"] is True and b["write_workflow"] is True and b["push_image"] is True


def test_the_restricted_default_can_only_read() -> None:
    b = _b("不写 permissions:（受控默认）")
    assert b["write_code"] is False and b["push_image"] is False and b["read_secrets"] is True


def test_switching_everything_off_also_removes_the_oidc_route() -> None:
    b = _b("permissions: {}")
    assert b["write_code"] is False and b["cloud_creds"] is False


def test_raising_the_token_per_job_is_the_shape_that_works() -> None:
    b = _b("contents: read ＋ 部署 job")
    assert b["write_code"] is False and b["cloud_creds"] is True


def test_the_pull_request_target_shape_has_three_things_at_once() -> None:
    b = _b("pull_request_target")
    assert b["write_code"] is True and b["read_secrets"] is True


def test_five_grants_and_only_the_first_pushes_images() -> None:
    assert len(P.GRANTS) == 5
    assert [g.name for g in P.GRANTS if P.blast_radius(g)["push_image"]] == [
        "不写 permissions:（宽松默认）"]


def test_secrets_are_not_passed_to_a_fork_pull_request() -> None:
    """官方：除 `GITHUB_TOKEN` 外，fork 触发的工作流拿不到密钥。"""
    event = next(e for e in P.EVENTS if e.name.startswith("fork"))
    assert event.secrets is False and event.token_write is False


def test_a_missing_secret_arrives_as_an_empty_string() -> None:
    event = next(e for e in P.EVENTS if e.name.startswith("fork"))
    v = P.secret_value(event)
    assert v["value"] == "" and v["empty"] is True
    assert "401" in v["symptom"], "失败现场指向服务端"


def test_the_privileged_trigger_does_see_the_secrets() -> None:
    event = next(e for e in P.EVENTS if e.name == "pull_request_target")
    assert event.secrets is True and event.token_write is True


def test_dependabot_events_do_not_get_secrets_either() -> None:
    event = next(e for e in P.EVENTS if e.name.startswith("Dependabot"))
    assert event.secrets is False


def test_oidc_tokens_live_for_one_job() -> None:
    oidc = P.CREDENTIALS[1]
    assert oidc["valid_seconds"] == 300 and oidc["copies"] == 0
    assert oidc["rotate_by"].startswith("没有人")


def test_a_long_lived_secret_needs_a_human_to_rotate_it() -> None:
    long_lived = P.CREDENTIALS[0]
    assert long_lived["copies"] == 2 and long_lived["valid_seconds"] == 90 * 24 * 3600
    assert long_lived["rotate_by"].startswith("人")


def test_the_leak_window_follows_the_lifetime() -> None:
    assert P.CREDENTIALS[0]["valid_seconds"] > 1000 * P.CREDENTIALS[1]["valid_seconds"]


def test_a_tag_can_be_moved_but_a_sha_cannot() -> None:
    assert P.PINS[0].mutable is True and P.PINS[1].mutable is False


def test_pinning_to_a_sha_is_the_only_immutable_form() -> None:
    assert "唯一" in P.PINS[1].note
