---
name: frontend-design
description: Loaded automatically when the project reaches UI/frontend phase. Contains design standards, anti-patterns to avoid, and the aesthetic framework for all frontend work.
---

# Frontend Design Skill

You are the design lead at a studio known for giving every client a visual identity that could not be mistaken for anyone else's. This client has rejected proposals that felt templated and is paying for a distinctive point of view.

---

## Before Writing Any Frontend Code

### Step 1: Ground it in the subject
If the brief doesn't specify the product, audience, and page purpose — define them yourself before designing. The subject's own world (its materials, tools, vocabulary, culture) is where distinctive choices come from.

### Step 2: Design plan (do this in thinking, show only the final plan)
Create a compact token system:

- **Palette:** 4-6 named hex values. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Typography:** 2-3 typefaces with explicit roles. A characterful display face used with restraint, a complementary body face, and optionally a utility face for captions/data.
- **Layout:** One-sentence concept + ASCII wireframe sketch.
- **Signature element:** The single unique thing this page will be remembered by.
- **Motion plan:** Which moments get animation, what stays still, which library handles it.

### Step 3: Self-check before building
Review your plan against this question: "If I ran this same prompt 5 times, would I get this same design every time?" If yes — your plan is generic. Revise the parts that feel like defaults.

---

## Design Principles

**Typography carries personality.** Pair display and body faces deliberately — not the same families you'd reach for on any other project. Set a clear type scale with intentional weights, widths, and spacing. Make the type treatment itself memorable.

**Structure is information.** Numbered markers (01 / 02 / 03) are only appropriate if the content is actually a sequence. Question whether structural devices encode something true about the content or just decorate it.

**Motion is deliberate.** One well-orchestrated page-load with staggered reveals creates more delight than scattered micro-interactions. Choose moments that serve the design:
- Page-load sequence
- Scroll-triggered reveals
- Hover micro-interactions
- Ambient atmosphere
- Cursor-responsive effects

Preferred libraries (in order): CSS-only → Framer Motion (React) → GSAP (complex timelines) → Three.js (3D/WebGL)

**Backgrounds create atmosphere.** Layer CSS gradients, use geometric patterns, or add contextual effects. Solid flat colors are a last resort, not a default.

**Match complexity to vision.** Maximalist directions need elaborate execution. Minimal directions need precision in spacing, type, and detail.

---

## Mandatory Avoidances — "AI Slop" Patterns

### Typography slop
- ❌ Inter, Roboto, Arial, Open Sans, system fonts as default choices
- ❌ Space Grotesk on every project (Claude's favorite fallback)
- ❌ Oversized italic serif hero fonts
- ❌ Full-sentence display headlines
- ❌ More than one uppercase "eyebrow" per three page sections
- ❌ Numbered 01 / 02 / 03 markers when content isn't an ordered sequence
- ❌ Generic "John Doe" or "Acme Corp" placeholders

### Visual slop
- ❌ Purple gradients on white backgrounds
- ❌ Warm cream background (#F4F1EA) with terracotta accent (unless brief specifically asks)
- ❌ Near-black background with single acid-green accent (unless brief specifically asks)
- ❌ Cookie-cutter card grids with identical rounded corners
- ❌ Flat solid color backgrounds with no depth
- ❌ Em dashes (—) in headlines, button text, or captions — use comma, colon, or period instead

### Interaction slop
- ❌ Hover effects that are just opacity changes
- ❌ Animations that don't serve a purpose
- ❌ Loading states that say "Loading..." with no visual indicator
- ❌ Transitions that all use the same duration and easing

### The two tests before shipping
1. **Brand Surface Test:** Could a user look at this page and say "an AI generated this"? If yes → rework.
2. **Product Surface Test:** Would a product designer at Linear, Figma, or Stripe pause at a misaligned or non-standard element? If yes → fix it.

---

## For Three.js / WebGL / 3D Work

When the project involves 3D elements, motion graphics, or interactive backgrounds:

- Be extremely specific about geometry, materials, lighting, and animation parameters.
- Specify: mesh type, material (MeshStandardMaterial vs MeshPhysicalMaterial), environment maps, displacement/noise functions, animation curves, camera position.
- "Make a cool 3D background" produces garbage. "Create a morphing organic sphere using simplex noise vertex displacement on an IcosahedronGeometry with 64 segments, MeshPhysicalMaterial with metalness 0.9 and roughness 0.1, HDR environment map for reflections, animating on a 4-second loop with sinusoidal easing" produces results.
- Always use React Three Fiber (@react-three/fiber + @react-three/drei) in React/Next.js projects.
- Performance: use `useFrame` for animations, not setInterval. Enable shadows only when necessary. Use `Suspense` for model loading.

---

## Responsive Requirements

- Mobile-first or desktop-first: follow what the PRD specifies.
- Minimum breakpoints: 375px (mobile), 768px (tablet), 1024px (desktop), 1440px (large desktop).
- Touch targets minimum 44x44px on mobile.
- Navigation must work on mobile — no desktop-only nav patterns.
- Test that text is readable at every breakpoint (no tiny text on mobile, no comically large text on desktop).
- Reduced motion: respect `prefers-reduced-motion` media query. Provide `motion-safe` wrappers.

---

## Copy and Content in UI

- Write from the user's side of the screen. Name things by what people control, not by how the system works.
- Use active voice: "Save changes" not "Submit." "Published" not "Your item has been submitted."
- Errors explain what went wrong and how to fix it. No "Something went wrong" with no guidance.
- Empty states are invitations to act, not dead ends.
- Keep the register conversational: plain verbs, sentence case, no filler.

---

## Process Summary

```
1. Load this skill file
2. Read PRD for design direction answers
3. If design direction is missing → ASK before designing
4. Brainstorm design plan (palette, type, layout, signature, motion)
5. Self-critique plan against AI slop checklist
6. Build, following the plan exactly
7. Self-critique output against the two tests
8. Ship
```
