from gateway.announce import AnnounceRouter


def test_announce_routing_domain_category_default(tmp_path):
    cfg = tmp_path / "announce_routing.yaml"
    cfg.write_text(
        """
routes:
  domain:
    design: "discord:#design"
  category:
    marketing: "telegram:-100222"
  default: "telegram"
""".strip(),
        encoding="utf-8",
    )

    router = AnnounceRouter(config_path=cfg)
    assert router.resolve_target(domain="design") == "discord:#design"
    assert router.resolve_target(category="marketing") == "telegram:-100222"
    assert router.resolve_target(domain="other") == "telegram"
