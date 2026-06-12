# Antenna Result Diagnosis And Next-Mutation Rules

## Purpose

Use this guide to convert CST results into the next structural hypothesis. The agent must identify the issue, evidence, likely physical causes, proposed geometry or parameter mutation, expected improvement, and risks.

## Diagnostic Inputs

Collect first:

- `S11`, `S21`, multi-port isolation, VSWR.
- -10 dB bandwidth or the user's specified threshold.
- In-band gain, efficiency, pattern, 3 dB beamwidth, front-to-back ratio, sidelobes.
- Polarization, axial ratio, cross-polarization.
- Current distribution, near-field, and far-field monitors.
- Mesh settings, port modes, boundary distance, and simulation logs.

Confirm metric source and frequency before combining results from different monitors or design versions.

## Matching Issues

### Resonance Too High

Likely causes:

- Effective current path is too short.
- Equivalent capacitance or coupling is insufficient.
- Substrate or air-layer assumptions are wrong.

Candidate mutations:

- Lengthen the main current path, add slots, meanders, or branches.
- Increase coupling length or add parasitic elements.
- Add local capacitive loading or adjust feed position.

Risks:

- Larger size or lower efficiency.
- New modes may affect radiation pattern.

### Resonance Too Low

Candidate mutations:

- Shorten the current path.
- Reduce slot or branch length.
- Reduce coupling or capacitive loading.
- Move the feed to a better impedance region.

### S11 Is Shallow But Frequency Is Close

Candidate mutations:

- Tune feed position, feedline width, feed gap, or matching stub.
- Fine-tune coupling distance.
- Preserve radiator length and prioritize impedance matching structures.

### Bandwidth Too Narrow

Candidate mutations:

- Introduce a nearby resonance with parasitic elements, slots, stacked structures, or coupled branches.
- Increase effective thickness or air gap.
- Change feed coupling.
- Optimize resonance spacing in multi-resonance structures.

Risks:

- Extra resonances may degrade pattern or efficiency.

## Gain And Efficiency Issues

### Low Gain But High Efficiency

Likely causes:

- Aperture is small, pattern is too broad, or array aperture is insufficient.
- Radiation is not directed toward the target region.

Candidate mutations:

- Increase effective aperture.
- Add reflectors, parasitic directors, metasurfaces, or array elements.
- Adjust ground plane or reflector size.

### Low Efficiency

Likely causes:

- High metal or dielectric loss.
- Strong current is concentrated in narrow slots, thin traces, lossy dielectric, or matching network.
- Miniaturization is too aggressive.

Candidate mutations:

- Reduce narrow gaps and high-current bottlenecks.
- Use lower-loss material or reduce electric field in lossy regions.
- Relax miniaturization and reduce excessive loading.

### Abnormal Pattern

Candidate mutations:

- Check boundaries and air-box distance.
- Check port mode and reference plane.
- Adjust ground, parasitic structures, or array phase.
- Check whether structural asymmetry increases cross-polarization.

## Multi-Port And Array Issues

### Poor Isolation

Candidate mutations:

- Add decoupling stubs, ground slots, parasitic isolators, EBG/metasurface structures.
- Adjust element spacing and polarization.
- Check feed-network coupling.

### Scanning Or Beam Problems

Candidate mutations:

- Check whether array spacing creates grating lobes.
- Adjust amplitude and phase tapering.
- Check edge elements and periodic boundary settings.

## Simulation-Setup Diagnosis

Rule out non-geometry problems first:

- Port does not contact the intended conductor.
- Boundary is too close to the antenna.
- Far-field monitor frequency is not the target frequency.
- Mesh is too coarse for stable S-parameters or efficiency.
- Results are from an older design version.
- Project was not rebuilt or parameters were not applied.

## Next-Step Format

```yaml
diagnosis:
  issue: resonance_high | poor_matching | narrow_bandwidth | low_gain | low_efficiency | bad_pattern | poor_isolation
  evidence: metrics and source paths
  likely_causes: ranked physical causes
proposed_mutation:
  mutation_id: next mutation id
  parent_design_id: current design id
  operation: add_slot | adjust_feed | add_parasitic | edit_ground | add_via | parameter_tune
  target_objects: CST object names
  parameters: proposed values or bounds
  expected_effect: what should improve
  risks: possible tradeoffs
validation:
  required_results: S11, farfield, efficiency, logs
  accept_rule: objective threshold
  rollback_rule: when to reject
```

## Do Not

- Do not judge a final antenna only from one S11 curve.
- Do not ignore efficiency, pattern, ports, or boundaries.
- Do not use old-version results as new-structure results.
- Do not claim optimization success without metric sources.
- Do not reduce a multi-objective design problem to a single minimum S11 value.
