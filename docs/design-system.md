# Daily Win — Design System (V0.2.2)

The interface is designed for the **parent/guardian**, not for a child operating the app alone.

AI is a copilot for the parent. The child is the learner. Screens, copy, and visual hierarchy assume an adult is planning, coaching, and reflecting — usually with the child nearby, not with the child driving the phone.

## Visual principles

Daily Win should feel like a calm, trustworthy early-stage product:

- **Warm** — cream environment, not clinic white
- **Trustworthy** — deep teal for action, charcoal for information
- **Calm** — generous whitespace, few competing CTAs
- **Modern** — restrained surfaces, not skeuomorphic
- **Easy to scan** — one primary action per screen
- **Slightly playful** — gold used sparingly for the idea of a “Win”

It should not look cartoonish, babyish, like school software, enterprise SaaS, a medical app, or an over-gamified kids product.

Do not copy Duolingo, Khan Academy Kids, Lovevery, or Apple visual systems. Use established layout principles with a distinct Daily Win identity.

**Identity:**

| Role | Color idea | Meaning |
| --- | --- | --- |
| Trust / action | Deep green/teal | Primary interaction |
| Environment | Warm cream | Calm parent workspace |
| Win / delight | Gold | Completion, spark, “Win” moments |
| Information | Charcoal | Serious readable content |

Color communicates purpose. It does not decorate every component.

## Appearance / dark mode

V0.2.2 is **intentionally light-only** for the demo.

Semantic token names are stable so a dark theme can be added later without renaming application code (`background`, `surface`, `textPrimary`, `actionPrimary`, and so on). Do not invent a half-finished dark palette for this demo. The app does not follow system dark appearance.

## Color tokens

Source: `apps/mobile/src/theme/colors.ts`

Use semantic names in application code. Do not use decorative names such as `teal500`.

| Token | Hex | Use |
| --- | --- | --- |
| `background` | `#FAF8F3` | Screen canvas |
| `surface` | `#FFFFFF` | Cards, inputs, secondary buttons |
| `surfaceMuted` | `#F3F0E8` | Quiet grouping, pending badges |
| `textPrimary` | `#1F2B28` | Body, titles, text on cream/gold surfaces |
| `textSecondary` | `#5E6B66` | Captions, supporting copy |
| `textOnAction` | `#FFFFFF` | Text on primary/danger buttons only |
| `borderSubtle` | `#D9E1DD` | Hairlines, input borders, secondary buttons |
| `actionPrimary` | `#2E6F62` | Primary buttons, selected chip border, links |
| `actionPrimaryPressed` | `#24584E` | Pressed primary (if needed) |
| `actionPrimarySoft` | `#EAF3EF` | Selected chips, success badges, “next” cards |
| `highlight` | `#F4C76E` | Win spark / accent marks only — never small text on white |
| `highlightSoft` | `#FFF5D8` | Win card, “What changed today”, Adapted / Completed badges |
| `danger` | `#B54845` | Errors, destructive demo confirmation — not primary CTAs |
| `dangerSoft` | `#F6E6E5` | Error callout background |
| `phaseLearn` | `#5C7388` | LEARN accent only |
| `phaseDo` | `#C4922A` | DO accent only |
| `phaseGrow` | `#2E6F62` | GROW accent only |

Gold (`highlight`) is never used as small text on white. Dark text sits on gold or pale-gold surfaces.

Do not introduce a rainbow palette. Phase accents are marks beside labels; body text stays `textPrimary`.

## Typography

Source: `apps/mobile/src/theme/typography.ts`

**Nunito** (`Nunito_700Bold`, `Nunito_800ExtraBold`) is used only for personality:

- Display / hero (`display`, ~32)
- Screen titles (`screenTitle`, ~26)
- Card titles (`cardTitle`, ~20)

**Native system font** is used for everything a parent has to read carefully:

- Body (`body`, 17 regular)
- Emphasized body (`bodyEmphasized`, 17 semibold)
- Secondary (`secondary`, 15)
- Caption / metadata (`caption`, 13 medium)
- Section labels (`sectionLabel`, 12 semibold, limited uppercase + letter spacing)
- Buttons (`button`, 17 semibold)
- Forms and long AI-generated text (`GeneratedText`)

Do not set long generated content in all caps. Section labels may use limited uppercase; paragraphs must not.

Dynamic Type is allowed (React Native default font scaling). Layouts use wrapping, `flexShrink`, and no fixed content heights so larger text can grow.

## Spacing

Source: `apps/mobile/src/theme/spacing.ts`

Scale: **4 / 8 / 12 / 16 / 20 / 24 / 32 / 40**

| Token | Value | Typical use |
| --- | --- | --- |
| `xxs` | 4 | Tight internal gaps |
| `xs` | 8 | Related items |
| `sm` | 12 | Compact clusters |
| `md` | 16 | Default stack gap |
| `lg` | 20 | Page padding, card padding |
| `xl` | 24 | Section separation |
| `xxl` | 32 | Large section separation |
| `xxxl` | 40 | Screen bottom inset |
| `screenX` | 20 | Phone horizontal page padding |
| `card` | 20 | Card internal padding |
| `section` | 32 | Major blocks |

Whitespace is part of the design. Prefer a divider + type over stacking extra bordered cards.

## Radius and surfaces

Source: `apps/mobile/src/theme/radius.ts`

| Token | Value | Use |
| --- | --- | --- |
| `card` | 16 | Cards |
| `button` | 16 | Primary / secondary / danger buttons |
| `chip` | 12 | Choice chips |
| `chipPill` | 999 | Status badges, phase dots |
| `input` | 14 | Text fields |

Prefer surface differentiation, a subtle border, and very light elevation. Avoid floating Material-style shadows. Not every section needs a card.

## Buttons

`AppButton` and `TextButton` in `apps/mobile/src/ui/`.

**Primary**

- Teal (`actionPrimary`) background, white text
- ~52px visual height, ≥44pt hit area
- 17 semibold
- Pressed: ~0.88 opacity + `0.98` scale, ~110ms
- One primary button per view

**Secondary**

- White / surface, teal text, subtle border
- Same height as primary
- Used for alternate paths (Create a demo profile, Back to Home, Edit profile)

**Danger**

- `danger` fill, white text
- Demo destructive actions in Demo Controls stay muted text buttons, not brand-primary

**Text button**

- Teal label, no fill, ≥44pt hit area
- Back, “View completed Win”, quiet navigation

Never present two equally prominent primary buttons on one screen.

## Cards and chips

- **Card `surface`** — default grouping when a surface is actually needed
- **Card `soft`** — planned adjustment / “what changes next”
- **Card `highlight`** — Win moments and “What changed today”
- **ChoiceChip** — generous touch area, selected = check icon + stronger teal border + `actionPrimarySoft` (not color-only)
- **StatusBadge** — quiet; Completed / Reflection pending / Adapted. No neon states

## Motion

Source: `apps/mobile/src/theme/motion.ts`

Motion communicates state. It is not decoration.

| Token | Duration | Use |
| --- | --- | --- |
| `instant` | 110ms | Button / chip press |
| `fast` | 180ms | Small fades |
| `normal` | 240ms | Learn/Do/Grow reveal |
| `success` | 320ms | Brief success transitions (cap) |
| `pressScale` | 0.98 | Pressed controls |
| `enterOffset` | 8px | Gentle vertical enter |

Allowed: opacity, 4–8px vertical movement, subtle scale on press.

Avoid: bounce, large horizontal travel, spinning cards, confetti, endless pulsing, animation before every navigation.

**Reduce Motion:** skip travel; prefer instant state changes or a short fade. Never make the parent wait for an animation to finish before they can act.

## Haptics

`apps/mobile/src/lib/haptics.ts` (expo-haptics). Failures are swallowed so haptics never block the flow.

Used sparingly:

- Successful reflection save
- Chip selection confirmation
- Successful demo reset / restart confirmation

Do not vibrate on every tap.

## Iconography

One system: **Ionicons** via `@expo/vector-icons`, wrapped by `Icon`.

Icons support labels. They do not replace important text. No clipart, no mixed icon packs.

Typical uses: check, spark/win, book/learn, movement/do, growth/leaf, history, profile.

## Layout and responsiveness

`Screen` applies Safe Area, 20px horizontal padding, and a **max content width of 680** centered on tablets / web.

- Mobile-first
- No fixed content heights
- No horizontal overflow
- `flexWrap` / `flexShrink` on chips, nav, badges
- Phone padding ~20
- Wider devices: do not stretch paragraphs edge to edge

Web is useful for visual QA. It is not proof of iPhone-native behavior.

## Accessibility

- ≥44×44pt touch targets
- `accessibilityRole`, `accessibilityLabel`, `accessibilityState.selected` / `disabled` / `busy`
- Loading announced (`progressbar` / live status copy)
- Selection is never color-only (check + border + background)
- Text/background contrast ≥ 4.5:1 for normal text
- Gold is not small text on white
- Respect Reduce Motion
- Reasonable Dynamic Type; no layouts that collapse when text scales

## Empty, error, loading

Reusable: `EmptyState`, `ErrorCallout`, `ScreenLoading`.

- **Loading:** small spinner + one clear sentence; keep surrounding layout. Generation may rotate 2–3 supportive status lines. Those lines are **general status**, not backend pipeline telemetry. No fake percentages.
- **Empty:** simple icon + sentence + relevant CTA. Expected empty states are not failures.
- **Error:** small danger accent, plain language, Retry.

## Development controls

`DemoControls` sits at the bottom of Home / first-run. Muted styling. Not part of the parent product.

Shows: Demo V0.2.2, Tester fingerprint, Backend status, then Reset activity history / Restart demo from beginning / Test feedback.

Destructive demo actions do not use the primary teal button treatment.

## Parent-facing product moments

| Screen | One main thing |
| --- | --- |
| First-run | Try the Hayes demo |
| Home | Today’s Win (generate, view, or reflect) |
| Onboarding | Next / Create demo profile |
| Daily Win | Start with [child] |
| Started Win | Do the activity, then reflect |
| Reflection | Save reflection |
| Insight | Generate the next Daily Win |
| Progress | Understand what the system learned |
| History | Open a past Win |
| Profile | Review / edit parent-controlled context |

Gold is reserved for Win / completion. Primary interaction remains teal.

## Token and component map

```
apps/mobile/src/theme/
  colors.ts
  spacing.ts
  typography.ts
  radius.ts
  motion.ts
  index.ts

apps/mobile/src/ui/
  Screen.tsx
  AppText.tsx
  AppButton.tsx
  TextButton.tsx
  Card.tsx
  StatusBadge.tsx
  SectionLabel.tsx
  ChoiceChip.tsx
  ChipPicker.tsx
  EmptyState.tsx
  ErrorCallout.tsx
  ScreenLoading.tsx
  PhaseBadge.tsx
  DemoControls.tsx
  GeneratedText.tsx
  Icon.tsx
```
