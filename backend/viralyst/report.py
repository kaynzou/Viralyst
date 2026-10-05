"""Turn simulation results into something a human can read."""

from collections import Counter

from .algorithm import WEIGHTS, engagement_rates, signal_strengths
from .models import Reaction, VideoBrief, WaveResult
from .simulation import furthest_stage

STAGES = {
    1: "FLOP: stalled with your followers",
    2: "NICHE: reached similar people but didn't break out",
    3: "SOLID: made it to Explore, then cooled off",
    4: "STRONG: reached a broad audience before slowing down",
    5: "VIRAL: still spreading after the biggest wave",
}

TIPS = {
    "watch": "People leave early. Make the first 3 seconds show the payoff, and cut anything slow.",
    "share": "Nothing makes people send it to a friend. Add a surprising result, a relatable pain, or a 'this is so you' moment.",
    "save": "No reason to save it. Add a concrete tip, steps, or a number people will want to come back to.",
    "comment": "Few comments. End on a question or a mildly bold opinion people want to answer.",
    "like": "Low overall appeal. The idea may be unclear: say what the product does in one sentence, early.",
    "follow": "Viewers don't follow. Make it obvious what else they'll get from your account.",
}


def print_report(video: VideoBrief, results: list[WaveResult], seed: int) -> None:
    reactions = [r for wave in results for r in wave.reactions]
    stage = furthest_stage(results)
    reach = sum(wave.wave.represents for wave in results)

    print()
    print(f'VIRALYST  "{video.title}"')
    print(f"Simulated {len(reactions)} viewers across {len(results)} wave(s). Seed {seed} (use --seed {seed} to repeat this run).")
    print()
    print_wave_table(results)
    print()
    print(f"Verdict:      {STAGES[stage]}")
    print(f"Rough reach:  ~{reach:,} people (an uncalibrated guess for now)")
    print()
    print_segments(reactions)
    print()
    print_signals(reactions)
    print()
    print_sample_viewers(results[0].reactions)
    print()


def print_wave_table(results: list[WaveResult]) -> None:
    print(f"{'Wave':<5}{'Shown to':<24}{'Viewers':>8}{'Target':>8}{'Watch':>7}{'Like':>6}{'Cmnt':>6}"
          f"{'Share':>7}{'Save':>6}{'Follow':>8}{'Score':>7}  Decision")
    for result in results:
        r = result.rates
        target = sum(x.persona.in_target for x in result.reactions) / len(result.reactions)
        decision = "push" if result.passed else "stop"
        print(f"{result.number:<5}{result.wave.label:<24}{len(result.reactions):>8}{target:>8.0%}"
              f"{r['watch']:>7.0%}{r['like']:>6.0%}{r['comment']:>6.0%}{r['share']:>7.0%}{r['save']:>6.0%}"
              f"{r['follow']:>8.0%}{result.score:>7.2f}  {decision} (needs {result.threshold:.2f})")


def print_segments(reactions: list[Reaction]) -> None:
    scrolled = sum(r.scrolled_past for r in reactions) / len(reactions)
    print(f"First impression: {scrolled:.0%} of viewers scrolled past within a second or two.")
    if scrolled > 0.5:
        print("  That's your #1 problem: the first 3 seconds don't stop the scroll. Fix the hook before anything else.")
    for label, in_target in [("Target audience", True), ("Everyone else", False)]:
        group = [r for r in reactions if r.persona.in_target == in_target]
        if group:
            rates = engagement_rates(group)
            print(f"  {label:<16}{len(group):>4} viewers   watched {rates['watch']:.0%}   "
                  f"liked {rates['like']:.0%}   shared {rates['share']:.1%}")


def print_signals(reactions: list[Reaction]) -> None:
    strengths = signal_strengths(engagement_rates(reactions))
    print("Signals compared with a typical reel (1.0x = typical):")
    for signal in WEIGHTS:
        bar = "#" * round(strengths[signal] * 10)
        print(f"  {signal:<8}{strengths[signal]:>5.1f}x  {bar}")
    weakest = min(strengths, key=strengths.get)
    print(f"Weakest signal: {weakest}. Tip: {TIPS[weakest]}")


def print_sample_viewers(reactions: list[Reaction], count: int = 5) -> None:
    print("A few of your followers:")
    for r in reactions[:count]:
        p = r.persona
        actions = [name for name, did in [("liked", r.liked), ("commented", r.commented),
                   ("shared", r.shared), ("saved", r.saved), ("followed", r.followed)] if did]
        what = "scrolled past" if r.scrolled_past else f"watched {r.watch_fraction:.0%}" + "".join(f", {a}" for a in actions)
        print(f"  {p.name:<11} {p.age:>2}, into {'/'.join(p.interests):<30} {what}")


def print_many_runs(video: VideoBrief, all_results: list[list[WaveResult]]) -> None:
    counts = Counter(furthest_stage(results) for results in all_results)
    n = len(all_results)
    print()
    print(f'VIRALYST  "{video.title}"  ({n} simulations)')
    print("How often each outcome happened:")
    for stage, label in STAGES.items():
        share = counts[stage] / n
        print(f"  {share:>5.0%}  {'#' * round(share * 40):<40}  {label}")
    print()
