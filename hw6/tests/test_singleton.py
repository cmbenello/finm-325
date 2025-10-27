from src.patterns.singleton import Config

def test_singleton_idempotent_init(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text('{"logging":{"level":"INFO"}}')

    c1 = Config(p)
    id1 = id(c1)

    q = tmp_path / "other.json"
    q.write_text('{"logging":{"level":"DEBUG"}}')
    c2 = Config(q)
    id2 = id(c2)
    
    assert id1 == id2

    assert c2["logging"]["level"] == "INFO"