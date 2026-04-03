# Design Spec Template

Path: `docs/plans/YYYY-MM-DD-{topic}-design-spec.md`

Exported by leader during `concluded` phase. This is the permanent record of the frontend design board outcome.

```markdown
# {Topic} Design Spec

> Date: {YYYY-MM-DD}
> Status: Approved ({accept_count}/{total} {unanimous/majority})
> Method: Frontend Design Board ({N}-member 2-phase structured debate)

## Summary
{2-3 sentence summary of the design direction and key specifications}

## Design Thinking Mapping

> This section maps directly to the frontend-design skill's Design Thinking input format.

- **Purpose**: {what problem this interface solves and who uses it}
- **Tone**: {selected aesthetic direction — e.g., "editorial minimalism with warm earth tones"}
- **Target User**: {who the design serves — demographics, context, needs}
- **Constraints**: {technical requirements, brand guidelines, accessibility requirements}
- **Differentiation**: {what makes this design unforgettable — the one thing someone will remember}

## Design Token Definition

### Color Tokens

| Token | Light | Dark | High Contrast |
|-------|-------|------|---------------|
| --color-surface | {value} | {value} | {value} |
| --color-on-surface | {value} | {value} | {value} |
| --color-primary | {value} | {value} | {value} |
| --color-accent | {value} | {value} | {value} |

### Typography Tokens

```css
--font-display: '{display font}', {fallback};
--font-body: '{body font}', {fallback};
--font-size-base: {value};
--line-height-base: {value};
--type-scale-ratio: {value};
```

### Spacing Tokens

```css
--space-unit: {base unit, e.g., 8px};
--space-xs: {value};
--space-sm: {value};
--space-md: {value};
--space-lg: {value};
--space-xl: {value};
```

### Motion Tokens

```css
--duration-fast: {value};
--duration-normal: {value};
--duration-slow: {value};
--easing-default: {value};
/* prefers-reduced-motion policy: {disable | shorten | alternative} */
```

### Elevation Tokens

```css
--shadow-sm: {value};
--shadow-md: {value};
--shadow-lg: {value};
```

## Responsive Strategy

- **Approach**: {mobile-first | desktop-first} — {rationale}
- **Breakpoints**:
  - sm: {value}
  - md: {value}
  - lg: {value}
  - xl: {value}

## Design Decisions
{Key design decisions from Phase 1 direction + Phase 2 specification with rationale}

## Unresolved Items
{Low-confidence claims, open questions, or items deferred for implementation. Omit section if none.}

## Minority Report
{Dissenting views from ratification, if any. Omit section if unanimous.}

## Discussion Artifacts
- Team: {comma-separated member names}
- Phase 1: {hypothesis_count} hypotheses, {critique_count} critiques
- Phase 2: {hypothesis_count} hypotheses, {critique_count} critiques
- Ratification: Phase 1 Round {N} ({count}/{total}), Phase 2 Round {N} ({count}/{total})
```

Note: This is a design specification, not an implementation plan. To create executable code, use the `frontend-design` skill with this Design Spec as input context.
