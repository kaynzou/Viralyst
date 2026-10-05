from viralyst.agent import MockAgent
from viralyst.simulation import WAVES, furthest_stage, run_cascade


def test_same_seed_gives_same_result(good_demo):
    video, audience = good_demo
    first = run_cascade(video, audience, MockAgent(), seed=11)
    second = run_cascade(video, audience, MockAgent(), seed=11)
    assert [w.score for w in first] == [w.score for w in second]


def test_cascade_stops_at_the_first_failed_wave(good_demo, weak_demo):
    for video, audience in [good_demo, weak_demo]:
        for seed in range(50):
            results = run_cascade(video, audience, MockAgent(), seed)
            assert all(w.passed for w in results[:-1])
            assert len(results) == len(WAVES) or not results[-1].passed


def test_waves_get_bigger(good_demo):
    video, audience = good_demo
    results = run_cascade(video, audience, MockAgent(), seed=1)
    sizes = [len(w.reactions) for w in results]
    assert sizes == sorted(sizes)


def test_good_demo_spreads_further_than_weak_demo(good_demo, weak_demo):
    def average_stage(demo):
        video, audience = demo
        stages = [furthest_stage(run_cascade(video, audience, MockAgent(), seed)) for seed in range(200)]
        return sum(stages) / len(stages)

    assert average_stage(good_demo) > 3.5
    assert average_stage(weak_demo) < 1.5
