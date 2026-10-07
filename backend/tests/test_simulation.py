from viralyst.agent import MockAgent
from viralyst.simulation import WAVES, run_cascade, simulate
from viralyst.summary import furthest_stage


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


def test_waves_arrive_one_at_a_time(good_demo):
    video, audience = good_demo
    waves = simulate(video, audience, MockAgent(), seed=7)
    first = next(waves)  # only wave 1 has been simulated at this point
    assert first.number == 1
    assert [w.number for w in waves] == [2, 3, 4]
