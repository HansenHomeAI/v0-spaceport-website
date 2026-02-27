<!-- e7e869a5-acc6-4823-b529-ce1298bcea2c 9809dd77-eef6-476b-8f7b-534cb9685a1e -->
# SOGS Viewer Implementation Plan

## Overview

Create a clean, minimal viewer for SOGS (Self-Organizing Gaussian Splats) files at `/web/app/sogs-viewer/page.tsx` using the official PlayCanvas SuperSplat library. The viewer will accept S3 URLs via a pill-shaped transparent input field.

## Technical Approach

### Library Integration

- Use PlayCanvas SuperSplat via CDN (no npm package needed)
- Load scripts: `playcanvas-stable.min.js` and `@playcanvas/supersplat@latest`
- API: `new SuperSplatViewer(canvas)` with `loadFromUrl(url)`

### File Structure

- **New Route**: `web/app/sogs-viewer/page.tsx`
- **Styles**: Inline styles or separate CSS file matching design system
- **Component**: React functional component with useEffect for PlayCanvas initialization

## Implementation Details

### 1. Page Component (`web/app/sogs-viewer/page.tsx`)

- Full-screen canvas container
- Centered pill-shaped input (transparent, matches design system)
- Input accepts S3 URL (directory path ending with `/`)
- Load button or auto-load on Enter
- Error handling for failed loads
- Loading state indicator

### 2. Design System Integration

- Input styling matches existing patterns:
- `border-radius: 999px` (pill shape)
- `background: rgba(255, 255, 255, 0.05)` (transparent)
- `border: 1px solid rgba(255, 255, 255, 0.2)`
- Focus state: `border-color: #FF4F00`
- Centered positioning
- Minimal UI (no extra controls)

### 3. PlayCanvas Integration

- Use `useEffect` to initialize PlayCanvas after component mount
- Create canvas element with ref
- Load SuperSplat scripts dynamically or via Next.js Script component
- Initialize `SuperSplatViewer` when URL is provided
- Handle canvas resize on window resize

### 4. S3 URL Handling

- Accept directory URL (e.g., `https://bucket.s3.amazonaws.com/path/to/sogs-bundle/`)
- Validate URL format
- Handle CORS errors gracefully
- Show error messages if load fails

### 5. State Management

- `s3Url`: string (input value)
- `loading`: boolean (loading state)
- `error`: string | null (error message)
- `viewerReady`: boolean (viewer initialized)

## Potential Hurdles & Solutions

### Hurdle 1: CDN Script Loading in Next.js

- **Solution**: Use Next.js `Script` component with `strategy="lazyOnload"` or load dynamically in `useEffect`

### Hurdle 2: TypeScript Types for SuperSplatViewer

- **Solution**: Create type declarations or use `@ts-ignore` for CDN-loaded global

### Hurdle 3: S3 CORS Configuration

- **Solution**: Document required CORS headers for S3 bucket (already handled in infrastructure)

### Hurdle 4: Canvas Sizing

- **Solution**: Use CSS to make canvas fill container, handle resize events

### Hurdle 5: URL Format Validation

- **Solution**: Validate URL ends with `/` (directory) and is valid S3 URL format

## Files to Create/Modify

1. **Create**: `web/app/sogs-viewer/page.tsx`

- Main viewer component
- Input field with pill styling
- PlayCanvas initialization
- Error handling

2. **Optional**: `web/app/sogs-viewer/styles.css`

- If styles are extensive, extract to separate file

## Testing Considerations

- Test with valid S3 URLs
- Test with invalid URLs
- Test CORS errors
- Test on mobile devices
- Verify canvas fills screen properly
- Test input focus states

## Dependencies

- No new npm packages needed (using CDN)
- PlayCanvas Engine (via CDN)
- PlayCanvas SuperSplat (via CDN)

## Success Criteria

- Clean, minimal UI with pill-shaped input
- Successfully loads SOGS files from S3 URLs
- Proper error handling and user feedback
- Canvas renders splats correctly
- Responsive design works on all devices

### To-dos

- [ ] Create web/app/sogs-viewer/page.tsx with React component structure
- [ ] Add pill-shaped transparent input field matching design system styles
- [ ] Load PlayCanvas Engine and SuperSplat scripts via Next.js Script component or dynamic loading
- [ ] Initialize SuperSplatViewer with canvas ref and handle loadFromUrl calls
- [ ] Implement error handling for failed loads, invalid URLs, and CORS issues
- [ ] Add loading indicators and state management for async operations
- [ ] Test with real S3 URLs and verify CORS configuration works