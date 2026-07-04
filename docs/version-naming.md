# AutoDS Version Naming

This document describes the version naming convention for AutoDS releases: **unique, catchy** alphabetical codenames that are short, memorable, and evocative of motion, roads, and energy; a fixed release cadence; and Long-Term Support (LTS) policy.

## Overview

| Aspect | Convention |
|--------|------------|
| **Codename theme** | Unique and catchy: short, punchy names (roads, motion, energy, flow) |
| **Alphabet cycles** | 3 full cycles (A–Z × 3 = 78 releases) |
| **Release cadence** | June and December (2 releases per year) |
| **LTS** | Every 4 years (every 8th release) |

## Release Schedule

- **June release** – First release of the calendar year.
- **December release** – Second release of the calendar year.

One full A–Z cycle = 26 releases = 13 years. Three cycles = 39 years of releases.

## Alphabetical Codename Cycles

Names are **unique and catchy**: one or two syllables where possible, easy to say and remember, evocative of driving, roads, flow, and forward motion—without sounding generic.

### Cycle 1 (A–Z)

| Letter | Codename  | Vibe |
|--------|-----------|------|
| A      | Asphalt   | The road; where it happens |
| B      | Blaze     | Fast, bright, unstoppable |
| C      | Crux      | The decisive point; core |
| D      | Drift     | Flow, control, motion |
| E      | Echo     | Resonance; lasting impact |
| F      | Flux      | Change, flow, momentum |
| G      | Glide     | Smooth motion; effortless |
| H      | Highway   | Open road; long run |
| I      | Ignite    | Start; spark; launch |
| J      | Jet       | Speed; out of the gate |
| K      | Kinetic   | Motion; energy in action |
| L      | Lane      | Your path; clear direction |
| M      | Meridian  | Peak; high point; noon |
| N      | Nexus     | Connection; hub; centre |
| O      | Orbit     | Loop; cycle; steady run |
| P      | Pulse     | Rhythm; heartbeat; alive |
| Q      | Quasar   | Far, bright, standout |
| R      | Ridge     | Crest; top of the climb |
| S      | Surge     | Push; burst of power |
| T      | Trail     | Path; journey; track |
| U      | Upturn    | Turn for the better |
| V      | Vista     | View ahead; horizon |
| W      | Waypoint  | Milestone; next stop |
| X       | Xenon    | Sharp light; clarity |
| Y      | Yield     | Give way; then flow |
| Z      | Zenith    | Top; peak; summit |

### Cycle 2 (A–Z)

| Letter | Codename  | Vibe |
|--------|-----------|------|
| A      | Apex      | Peak; tip; best point |
| B      | Bolt      | Quick; locked in; fast |
| C      | Cruiser   | Easy run; steady go |
| D      | Dash      | Short burst; sprint |
| E      | Edge      | Front; leading; sharp |
| F      | Forge     | Build; shape; advance |
| G      | Grid      | Structure; map; order |
| H      | Hub       | Centre; meeting point |
| I      | Inline    | Aligned; straight; true |
| J      | Jive      | In sync; in flow |
| K      | Key       | Essential; unlock |
| L      | Loop      | Cycle; round; return |
| M      | Metro     | Urban; connected; fast |
| N      | Nova      | New star; bright rise |
| O      | Oasis     | Rest stop; refresh |
| P      | Prism     | Many angles; clarity |
| Q      | Quest     | Mission; search; goal |
| R      | Rally     | Gather; push; comeback |
| S      | Spark     | Ignite; trigger; start |
| T      | Tide      | Turn; shift; wave |
| U      | Union     | Join; one system |
| V      | Volt      | Charge; energy; kick |
| W      | Wave      | Motion; roll; signal |
| X      | Xylem     | Flow; inner structure |
| Y      | Yonder    | Ahead; far; next |
| Z      | Zone      | Place; state; focus |

### Cycle 3 (A–Z)

| Letter | Codename  | Vibe |
|--------|-----------|------|
| A      | Arrow     | Direction; straight shot |
| B      | Breeze    | Easy; light; smooth |
| C      | Coast     | Cruise; steady; easy |
| D      | Drive     | Go; motive; push |
| E      | Ember     | Glow; lasting; warm |
| F      | Flare     | Flash; signal; stand out |
| G      | Grove     | Steady; rooted; grow |
| H      | Haze      | Soft; transition; shift |
| I      | Index     | Point; reference; order |
| J      | Joule     | Unit of energy; punch |
| K      | Kite      | Lift; free; light |
| L      | Lumen     | Light; clarity; output |
| M      | Mosaic    | Pieces; whole picture |
| N      | Nudge     | Small push; prompt |
| O      | Overdrive | Extra gear; push on |
| P      | Parkway   | Road; route; journey |
| Q      | Quota     | Target; mark; goal |
| R      | Radius    | Reach; scope; range |
| S      | Stride    | Step; pace; progress |
| T      | Torque    | Twist; power; pull |
| U      | Ultra     | Beyond; top tier |
| V      | Vector    | Direction; course |
| W      | Wavelength| In sync; tuned |
| X      | X-factor  | Extra; different; edge |
| Y      | Yard      | Short stretch; home base |
| Z      | Zest      | Energy; kick; life |

## Long-Term Support (LTS)

- **LTS interval**: Every **4 years** (every **8th** release).
- **Support**: LTS releases receive extended security and compatibility updates as defined by the project.
- **Planning**: Plan upgrades and migrations around the June/December cadence and the 4-year LTS markers.

### Example LTS timeline (illustrative)

If the first release is in **June 2025** (e.g. Asphalt):

- **2025 June** – Asphalt (1)  
- **2025 Dec** – Blaze (2)  
- **2026 June** – Crux (3)  
- **2026 Dec** – Drift (4)  
- **2027 June** – Echo (5)  
- **2027 Dec** – Flux (6)  
- **2028 June** – Glide (7)  
- **2028 Dec** – Highway (8) → **LTS**  
- …every 8th release is LTS (e.g. next LTS at Ignite, then Pulse, etc.).

## Version Format

Releases may be referred to as:

- **Codename only**: e.g. *AutoDS Asphalt*, *AutoDS Surge*.
- **Codename + date**: e.g. *AutoDS Asphalt (June 2025)*.
- **Semantic version** (if used): e.g. `2025.6.0` for June 2025, `2025.12.0` for December 2025.

Exact version numbering (e.g. 2025.6.0 vs 1.0.0) is defined by the project’s release process.

## Summary

- **78 named releases** across 3 A–Z cycles.
- **Two releases per year**: June and December.
- **LTS every 4 years** (every 8 releases).
- **Codename theme**: unique and catchy—short, punchy names (Asphalt, Blaze, Drift, Surge, Nexus, Zenith, etc.) evocative of roads, motion, and flow.

This gives a predictable, human-friendly version scheme for planning and communication.
