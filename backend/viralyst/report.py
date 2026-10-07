"""Turn simulation results into something a human can read."""

from .algorithm import WEIGHTS
from .models import Reaction, VideoBrief, WaveResult
from .summary import (STAGES, TIPS, all_reactions, furthest_stage, outcome_odds, reach, scroll_rate, segments,
                      signals, weakest)

def print_report(video: VideoBrief, results: list[WaveResult], seed: int) -> None:
    reactions = all_reactions(results)
    stage = furthest_stage(results)

    print()
    print(f'VIRALYST  "{video.title}"')
    print(f"Simulated {len(reactions)} viewers across {len(results)} wave(s). Seed {seed} (use --seed {seed} to repeat this run).")
    print()
    print_wave_table(results)
    print()
    print(f"Verdict:      {STAGES[stage]}")
    print(f"Rough reach:  ~{reach(results):,} people (an uncalibrated guess for now)")
    print()
    print_segments(reactions)
    print()
    print_signals(reactions, results[0].benchmarks)
    print()
    print_sample_viewers(results[0].reactions)
    print()
    if any(r.comment for r in reactions):
        print_comments(reactions)
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
    scrolled = scroll_rate(reactions)
    print(f"First impression: {scrolled:.0%} of viewers scrolled past within a second or two.")
    if scrolled > 0.5:
        print("  That's your #1 problem: the first 3 seconds don't stop the scroll. Fix the hook before anything else.")
    for label, key in [("Target audience", "target"), ("Everyone else", "others")]:
        if group := segments(reactions).get(key):
            print(f"  {label:<16}{group['viewers']:>4} viewers   watched {group['watch']:.0%}   "
                  f"liked {group['like']:.0%}   shared {group['share']:.1%}")


def print_signals(reactions: list[Reaction], benchmarks: dict[str, float] | None = None) -> None:
    strengths = signals(reactions, benchmarks)
    print("Signals compared with a typical reel (1.0x = typical):")
    for signal in WEIGHTS:
        bar = "#" * round(strengths[signal] * 10)
        print(f"  {signal:<8}{strengths[signal]:>5.1f}x  {bar}")
    worst = weakest(strengths)
    print(f"Weakest signal: {worst}. Tip: {TIPS[worst]}")


def print_sample_viewers(reactions: list[Reaction], count: int = 5) -> None:
    print("A few of your followers:")
    for r in reactions[:count]:
        p = r.persona
        actions = [name for name, did in [("liked", r.liked), ("commented", r.commented),
                   ("shared", r.shared), ("saved", r.saved), ("followed", r.followed)] if did]
        what = "scrolled past" if r.scrolled_past else f"watched {r.watch_fraction:.0%}" + "".join(f", {a}" for a in actions)
        who = f"{p.occupation} ({p.location.split(',')[0]})" if p.occupation else "into " + "/".join(p.interests)
        if len(who) > 44:
            who = who[:43] + "…"
        print(f"  {p.name:<11} {p.age:>2}, {who:<45} {what}")
        if r.thought:
            print(f'              thinking: "{r.thought}"')


def print_comments(reactions: list[Reaction], count: int = 8) -> None:
    commenters = [r for r in reactions if r.comment]
    print(f"What people commented ({len(commenters)} comments):")
    for r in commenters[:count]:
        who = "target audience" if r.persona.in_target else "outside target"
        print(f'  "{r.comment}"  ({r.persona.name}, {who})')


def print_many_runs(video: VideoBrief, all_results: list[list[WaveResult]]) -> None:
    odds = outcome_odds(all_results)
    print()
    print(f'VIRALYST  "{video.title}"  ({len(all_results)} simulations)')
    print("How often each outcome happened:")
    for stage, label in STAGES.items():
        share = odds[stage]
        print(f"  {share:>5.0%}  {'#' * round(share * 40):<40}  {label}")
    print()
