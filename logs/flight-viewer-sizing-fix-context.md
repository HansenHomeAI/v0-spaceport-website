# Flight Viewer Cesium Canvas Sizing Issue - Complete Context & Fix Prompt

## 🎯 THE PROBLEM

**Symptom**: Interactive 3D Cesium viewer only renders in the bottom half of its viewport container. Top half displays as black/empty space.

**Critical Metrics** (measured in browser automation):
- Container (`.flight-viewer__cesium-canvas`): **996px height** ✅
- Cesium Viewer (`.cesium-viewer`): **498px height** ❌ (should be 996px)
- Cesium Widget (`.cesium-widget`): **498px height** ❌
- Canvas elements: **2 canvases, both 498px height** ❌
- **Fill percentage: 50%** (viewer at exactly half container height)

**Visual Evidence**: Screenshot shows large black rectangle occupying top 50% of viewport, with interactive 3D map visible only in bottom half.

---

## 📋 ROOT CAUSE ANALYSIS

### Discovered Through Investigation:

1. **Initialization Timing Issue**: 
   - Cesium viewer is created during React mount
   - At creation time, flex layout hasn't fully settled → container reports smaller height (likely ~498px)
   - Cesium locks its internal dimensions based on container size at initialization
   - Even when container grows to 996px, Cesium's internal state remains locked at 498px

2. **Why CSS Fixes Failed**:
   - `height: 100%` in CSS doesn't work - Cesium overrides with computed pixel values
   - `flex: 1 1 0` approaches fail - Cesium calculates explicit heights internally
   - `!important` rules can't override JavaScript-set inline styles OR Cesium's internal canvas sizing

3. **Current State Analysis** (from browser evaluation):
   - Viewer element HAS inline `style.height="996px"` set ✅
   - But actual `clientHeight` is still **498px** ❌
   - This proves Cesium's internal canvas/widget sizing is overriding the DOM style

4. **Why Production Works but Dev Doesn't**:
   - Production builds likely have different CSS loading order
   - Or container height is stable before Cesium initializes in production
   - Dev builds have React StrictMode double-rendering + hot reload causing timing issues

---

## 🔧 ATTEMPTS MADE (All Failed)

### Attempt 1: CSS Flex Layout
- Changed container to `display: flex`
- Applied `flex: 1 1 0` to viewer/widget
- **Result**: Still 498px

### Attempt 2: CSS Height Overrides
- Added `height: 100% !important` to all Cesium elements
- **Result**: Still 498px

### Attempt 3: Wait for Stable Container Size
- Added `requestAnimationFrame` loop to wait for stable `clientHeight` before creating viewer
- **Result**: Still initializing at 498px

### Attempt 4: JavaScript Inline Height Forcing
- Created `forceViewerFill()` function setting inline `style.height` to container height
- Called after `viewer.resize()` and in ResizeObserver
- **Result**: Inline style shows 996px but `clientHeight` still 498px (Cesium internal override)

---

## 📁 KEY FILES

**Component**: `web/app/flight-viewer/page.tsx`
- Cesium viewer initialization: lines ~512-562
- Flight rendering effect: lines ~747-994
- Current fixes applied: `waitForStableContainerSize()` + `forceViewerFill()`

**Styles**: `web/app/flight-viewer/styles.css`
- Container styles: lines ~387-406
- Cesium overrides: lines ~408-442

**Global Styles**: `web/app/globals.css`
- Cesium widget imports: lines ~3-12

---

## 🔍 CURRENT BASELINE (Measured 2025-10-28)

```javascript
{
  containerHeight: 996px,        // ✅ Correct
  viewerHeight: 498px,           // ❌ Should be 996px
  widgetHeight: 498px,           // ❌ Should be 996px
  canvasHeights: [498, 498],     // ❌ Both should be 996px
  canvasCount: 2,                // ✅ Normal (Cesium uses 2 canvases)
  viewerInlineHeight: "996px",   // ✅ Set correctly
  widgetInlineHeight: "100%",    // ✅ Set correctly
  ISSUE: "BROKEN - Viewer at 50% height",
  VISUAL: "Black top half visible"
}
```

---

## 🎯 FIX PROMPT FOR CODING AGENT

### Your Mission:
Fix the Cesium viewer sizing issue where the viewer only fills 50% of its container (498px out of 996px), causing a black top half.

### Critical Requirements:
1. **Must use browser automation** (Playwright MCP) to verify fixes
2. **Must provide visual proof** (screenshots before/after)
3. **Must establish baseline** before making changes
4. **Must test incrementally** - one fix at a time, verify each step

### Steps:

#### Step 1: Establish Baseline
```javascript
// Navigate to http://localhost:3004/flight-viewer
// Upload Edgewood-1.csv file
// Wait 3 seconds for rendering
// Measure:
const baseline = {
  container: document.querySelector('.flight-viewer__cesium-canvas').clientHeight,
  viewer: document.querySelector('.cesium-viewer').clientHeight,
  widget: document.querySelector('.cesium-widget').clientHeight,
  canvases: Array.from(document.querySelectorAll('canvas')).map(c => c.height)
};
// Take screenshot: "flight-viewer-baseline.png"
// CONFIRM: viewer is 498px, container is 996px
```

#### Step 2: Investigate Cesium Internal State
```javascript
// Check what's actually controlling the height:
- Look for Cesium's internal canvas sizing code
- Check if there's a devicePixelRatio issue
- Verify if Cesium is using getBoundingClientRect() vs clientHeight
- Check for CSS transforms or scale() affecting layout
```

#### Step 3: Potential Solutions to Test (in order):

**Solution A: Force Canvas Resize via Cesium API**
- After viewer creation, explicitly set canvas dimensions:
```javascript
viewer.cesiumWidget.resize();
viewer.scene.canvas.width = container.clientWidth;
viewer.scene.canvas.height = container.clientHeight;
```

**Solution B: Use ResizeObserver with Debouncing**
- Wait for container size to stabilize for 100ms+ before calling viewer.resize()
- May need to detect when flex layout has fully computed

**Solution C: Delay Viewer Creation**
- Use `setTimeout` with longer delay (100-200ms) to ensure layout is stable
- Or use intersection observer to detect when container is in viewport

**Solution D: Absolute Positioning Workaround**
- Change container to `position: relative`, viewer to `position: absolute` with `inset: 0`
- This removes flex dependencies entirely

**Solution E: Check for Cesium Configuration**
- Review Cesium.Viewer constructor options
- May need to pass explicit dimensions or use different initialization approach

#### Step 4: Test Each Solution
- Make ONE change
- Reload page, upload file, measure heights
- Take screenshot
- If not fixed, revert and try next solution

#### Step 5: Success Criteria
- Container height = Viewer height = Widget height = Canvas heights
- All should be 996px (or container's full height)
- Screenshot shows NO black top half
- Viewer fills entire viewport

### Testing Commands:
```bash
# Dev server (already running on port 3004)
cd /Users/gabrielhansen/launchpad-spaceport-website/web && npm run dev:http

# Test file location
/Users/gabrielhansen/launchpad-spaceport-website/Edgewood-1.csv
```

### Key Observations from Previous Attempts:
1. **Inline styles are set correctly** but get overridden by Cesium internally
2. **Two canvases exist** - this is normal for Cesium (WebGL + 2D overlay)
3. **The issue is Cesium's internal sizing**, not CSS
4. **`viewer.resize()` is being called** but not working effectively
5. **ResizeObserver is set up** but container size appears stable (doesn't change after init)

### Critical Insight:
The viewer's DOM element shows `style.height="996px"` but `clientHeight` is 498px. This means Cesium is directly manipulating the canvas element dimensions or using a different sizing mechanism internally. The fix likely requires:
- Either manipulating Cesium's internal state directly
- Or ensuring the container size is stable BEFORE Cesium reads it
- Or using a different sizing approach that Cesium respects

---

## ✅ SUCCESS DEFINITION

**Fixed when:**
- `.cesium-viewer.clientHeight === .flight-viewer__cesium-canvas.clientHeight`
- All canvas elements have `height === container.clientHeight`
- Visual screenshot shows NO black top half - full viewport filled with 3D viewer
- Works consistently after page reload

**Evidence required:**
1. Browser automation measurement showing heights match
2. Screenshot proving visual fix
3. Test passes with different viewport sizes

---

## 🚀 NEXT STEPS

1. **Run baseline test** - confirm current broken state
2. **Try Solution A** - explicit canvas resize
3. **If fails, try Solution B** - debounced ResizeObserver  
4. **If fails, try Solution C** - delay viewer creation
5. **If fails, try Solution D** - absolute positioning
6. **Iterate until success**

**Remember**: Each fix must be tested with browser automation AND screenshots. Do not claim success without visual proof.

