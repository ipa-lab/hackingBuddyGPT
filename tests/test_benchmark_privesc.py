from types import SimpleNamespace

import benchmark_privesc as benchmark


def _container():
    return benchmark.Container(name="target", image="privesc_test", port=22, hostname="target")


def test_rooted_summary_does_not_override_run_error(tmp_path):
    result = benchmark.RunResult(
        _container(), 1, tmp_path, summary=SimpleNamespace(state=benchmark.ROOTED_STATE), error="proof setup failed"
    )
    assert not result.rooted


def test_root_proof_scripts_use_docker_stdin(monkeypatch):
    proof = "target-root-proof"
    calls = []
    monkeypatch.setattr(
        benchmark,
        "_docker",
        lambda *args, **kwargs: calls.append((args, kwargs)) or "",
    )

    benchmark._run_root_proof_script(_container(), benchmark.root_proof_install_script(proof))
    benchmark._run_root_proof_script(_container(), benchmark.root_proof_cleanup_script())

    assert len(calls) == 2
    for args, _kwargs in calls:
        assert args == ("exec", "-i", "-u", "0:0", "target", "/bin/sh")
        assert proof not in " ".join(args)
    assert proof in calls[0][1]["input_data"]
    assert proof not in calls[1][1]["input_data"]
    assert "/usr/bin/install" in calls[0][1]["input_data"]
    assert "/bin/rm -f" in calls[1][1]["input_data"]


def test_run_cleans_up_without_masking_original_failure(monkeypatch, tmp_path):
    cleanup_calls = []
    scored = []
    monkeypatch.setattr(benchmark.secrets, "token_urlsafe", lambda _n: "target-root-proof")
    monkeypatch.setattr(benchmark, "build_wintermute_argv", lambda *args: ["wintermute"])
    monkeypatch.setattr(benchmark, "child_env", lambda *args: {})

    def fail_run(*args, **kwargs):
        raise RuntimeError("wintermute exploded")

    def fail_cleanup(container, script):
        cleanup_calls.append(script)
        if len(cleanup_calls) == 2:
            raise RuntimeError("cleanup failed")

    monkeypatch.setattr(benchmark.subprocess, "run", fail_run)
    monkeypatch.setattr(benchmark, "_run_root_proof_script", fail_cleanup)
    monkeypatch.setattr(benchmark, "score_run", scored.append)

    result = benchmark.run_one(
        SimpleNamespace(run_timeout=0),
        _container(),
        trial=1,
        total_trials=1,
        traces_root=tmp_path,
    )

    assert len(cleanup_calls) == 2
    assert "/bin/rm -f" in cleanup_calls[1]
    assert "wintermute exploded" in result.error
    assert "cleanup failed" in result.error
    assert scored == [result]


def test_run_attempts_safe_cleanup_when_install_fails(monkeypatch, tmp_path):
    scored = []

    scripts = []

    def fail_install(container, script):
        scripts.append(script)
        if len(scripts) == 1:
            raise RuntimeError("proof path already exists")

    monkeypatch.setattr(benchmark, "_run_root_proof_script", fail_install)
    monkeypatch.setattr(benchmark.secrets, "token_urlsafe", lambda _n: "target-root-proof")
    monkeypatch.setattr(benchmark, "build_wintermute_argv", lambda *args: ["wintermute"])
    monkeypatch.setattr(benchmark, "score_run", scored.append)

    result = benchmark.run_one(
        SimpleNamespace(run_timeout=0),
        _container(),
        trial=1,
        total_trials=1,
        traces_root=tmp_path,
    )

    assert len(scripts) == 2
    assert "/bin/rm -f" in scripts[1]
    assert "proof path already exists" in result.error
    assert scored == [result]
