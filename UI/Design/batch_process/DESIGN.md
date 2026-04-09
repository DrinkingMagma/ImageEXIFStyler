# Design System Specification: The Lens & Frame

## 1. Overview & Creative North Star
**Creative North Star: "The Digital Gallery Curator"**
This design system rejects the "utility-only" aesthetic of standard Windows software. Instead, it treats the photography tool as a high-end editorial workspace. By leveraging intentional asymmetry, expansive breathing room, and tonal depth, we move away from a "grid of boxes" toward a "curated canvas." The interface acts as a silent partner to the photograph—authoritative and precise, yet visually receding to ensure the artist's work remains the sole focus.

## 2. Colors: Tonal Architecture
The palette is rooted in a monochromatic foundation to preserve color neutrality for photo editing. Interaction is signaled by a sophisticated teal (`tertiary`) and deep blue (`primary`) spectrum.

### The "No-Line" Rule
To achieve a premium, editorial feel, **1px solid borders are strictly prohibited for sectioning.** Structural boundaries must be defined solely through background color shifts or tonal nesting. 
- *Instead of a border:* Use `surface-container-low` for a sidebar against a `surface` main stage.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers—like stacked sheets of acrylic. 
- **Base Level:** `surface` (The foundation).
- **Secondary Level:** `surface-container-low` (Navigation or metadata panels).
- **Tertiary Level:** `surface-container-highest` (Pop-overs, context menus, or active image frames).

### The "Glass & Gradient" Rule
For floating elements (tooltips, floating toolbars), utilize "Glassmorphism." Apply `surface-container-high` with an 80% opacity and a `20px` backdrop-blur. 
Main CTAs should utilize a subtle linear gradient (Top-Left to Bottom-Right) from `primary` (#a3c9ff) to `primary-container` (#004883) to provide a "luminous" quality that feels etched rather than flat.

---

## 3. Typography: Editorial Precision
We utilize **Inter** for its mathematical clarity. The hierarchy is designed to make dense EXIF data readable while giving the UI an "art-book" feel.

| Role | Token | Specs | Intent |
| :--- | :--- | :--- | :--- |
| **Display** | `display-md` | 2.75rem / Tight tracking | Hero stats (e.g., ISO value). |
| **Headline**| `headline-sm` | 1.5rem / Medium weight | Section headers (e.g., "Metadata"). |
| **Title**   | `title-sm` | 1rem / Semi-bold | Field labels (e.g., "Aperture"). |
| **Body**    | `body-md` | 0.875rem / Regular | Primary EXIF data strings. |
| **Label**   | `label-sm` | 0.6875rem / All caps | Micro-annotations and units. |

*Editorial Note:* Use `secondary` (#9f9d9d) for unit labels (e.g., "mm" or "sec") to create a clear visual hierarchy between the value and the metric.

---

## 4. Elevation & Depth
In this system, depth is a function of light and tone, not structure.

*   **The Layering Principle:** Place a `surface-container-lowest` (#000000) card onto a `surface-container-low` (#131313) workspace to create a recessed "well" for the photo. 
*   **Ambient Shadows:** For floating dialogs, use a diffused shadow: `0px 12px 32px rgba(0, 0, 0, 0.4)`. The shadow must never be pure black; it should feel like a soft occlusion of ambient light.
*   **The "Ghost Border" Fallback:** If a divider is required for accessibility, use the `outline-variant` (#474848) at **15% opacity**. This creates a "suggestion" of a line rather than a hard break.

---

## 5. Components

### Action Buttons
- **Primary:** Gradient fill (`primary` to `primary-container`). Roundedness: `md` (0.375rem). Use `on-primary-fixed` for text.
- **Secondary:** Surface-only. Use `surface-bright` background with a `ghost border`. 
- **Tertiary:** No background. Text uses `primary` (#a3c9ff). For use in low-emphasis actions like "Cancel."

### The Precision Slider (Image Adjustments)
- **Track:** `surface-container-highest` (height: 4px).
- **Thumb:** `primary` (#a3c9ff) circle with a 2px `surface` ring.
- **Active State:** The track to the left of the thumb should glow with `tertiary` (#83fff6).

### EXIF Data Lists
- **Rule:** **Strictly no horizontal dividers.** 
- **Structure:** Use `body-md` for the value and `label-sm` (uppercase) for the key. 
- **Spacing:** Use 1.5rem of vertical white space between metadata groups to allow the eye to rest.

### Segmented Controls (View Switchers)
- **Container:** `surface-container-low`.
- **Selected Segment:** `surface-bright` with a `sm` (0.125rem) rounded corner. This creates a "pill-within-a-pocket" look that feels tactile.

### Custom Component: The "Metadata Ghost"
A specialized tooltip for hover states over the photo. Use the **Glassmorphism** rule: 70% opacity `surface-container-lowest` with a heavy backdrop blur and `primary` colored text.

---

## 6. Do's and Don'ts

### Do
- **Do** use `surface-container` shifts to define the sidebar. 
- **Do** use `tertiary` (#83fff6) sparingly—only for "Success" states or active photo-processing indicators.
- **Do** lean into `xl` (0.75rem) corner radii for large image containers to soften the "tech" feel.

### Don't
- **Don't** use 100% opaque `outline` tokens for borders; it destroys the "Gallery" aesthetic.
- **Don't** use shadows on buttons. Keep them flat or gradient-filled; reserve shadows for floating panels only.
- **Don't** use pure white text (#FFFFFF). Always use `on-surface` (#e7e5e5) to reduce eye strain in dark editing environments.