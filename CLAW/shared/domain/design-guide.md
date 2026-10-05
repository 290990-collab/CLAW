# Design guide

For projects where visual quality is a requirement, not a finishing touch. Overriding rule: **consistency before creativity** — one visual language, applied everywhere.

## Tokens are the single source

All style comes through a declared scale. No value written directly in a component.

- **Colour:** narrow palette, defined by **semantic role** (background, text, muted, accent, border, states) before by value. With multiple themes, the roles are the source and the absolute colours the consequence.
- **Typography:** one or two families, an explicit scale, defined weights, line height and spacing per level. Loading without shifting the content.
- **Spacing:** a coherent scale, never arbitrary margins. White space is a tool, not emptiness to fill.
- **Grid and breakpoints:** declared and named, with coherent maximum widths.
- **Motion:** durations and curves as tokens, so every animation speaks the same language.
- **Radii, shadows, borders:** these too as tokens.

Adding a token is a deliberate change — it is an internal contract used everywhere: first you look for whether a suitable one exists.

## Direction

- **Rigorous alignment:** every element is aligned to something. No positions set "by eye".
- **Readable hierarchy:** size, weight and space say what matters. The eye must know where to go without effort.
- **Reduce:** few families, a narrow palette, few elements per view. If an element serves no purpose, it goes.
- **Content guides form**, inside a single system: different treatments for different content, but the same tokens and the same grid.

## Motion

- **Motivated, not decorative:** it communicates continuity, hierarchy or feedback.
- **Short and natural:** the interface must feel responsive, not waiting for the animation.
- **Reduced-motion preference always respected** — it is not optional.
- **No harm:** no layout shifts, blocked scrolling, stolen focus or interaction prevented during the transition.

## Accessibility — a requirement, not an extra

Sufficient contrast for text and interactive elements · visible focus and a tab order consistent with reading · full keyboard use · text alternatives that say the function, not the appearance · adequate touch targets · correct semantic structure · no information carried by colour alone · forms with real labels and errors associated with the field.

## Performance as aesthetics

No content shifting after loading · images sized and served in the right format · fonts without a visual jump · heavy work off the rendering path · immediate response to interaction, even when the result arrives later. A slow interface is an ugly interface.

## Verification

Rendering is not deduced: it is looked at. Different widths, light and dark theme, long text and absent text, loading and error states, reduced motion, keyboard-only navigation. What was not looked at must be declared.

**Looking is not enough:** first the structured state — tree, computed sizes and styles, component state — then the image that confirms it. A single view proves nothing.

## In this project

[TO FILL IN — interface stack and libraries, where tokens and components live,
the visual direction already fixed, support constraints, how the environment is
started to look at the result, design tools connected.]
