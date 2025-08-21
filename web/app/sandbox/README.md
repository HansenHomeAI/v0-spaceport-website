# Spaceport Design System Sandbox

## 🎯 Purpose

This sandbox serves as a minimalist showcase of design components used specifically on the create page. It's designed to help standardize the website design by providing a clean, focused reference for developers.

## 🚀 Getting Started

### Access the Sandbox
Navigate to `/sandbox` in your browser to view the create page components.

### What You'll See
The sandbox is organized into focused sections:

1.  **Typography** - Text styles and headings
2.  **Buttons** - Primary and secondary actions
3.  **Form Elements** - Inputs, selects, toggles
4.  **Cards** - Project cards and waitlist
5.  **Upload** - Upload zones, progress, status
6.  **Modal** - Modal overlays and accordions
7.  **Map** - Map containers and search
8.  **Progress** - Progress bars and actions
9.  **Feedback** - Status messages and errors

## 🎨 Design Principles

### 1. Minimalism
- Clean, uncluttered design
- Consistent font weights (400)
- No unnecessary animations or effects
- Focus on functionality over decoration

### 2. Consistency
- Standardized typography scales
- Consistent spacing (16px, 24px, 32px)
- Unified component patterns
- Consistent border radius (16px)

### 3. Functionality
- Components work as intended
- Clear visual hierarchy
- Accessible design patterns
- Responsive behavior

## 🔧 Component Selector Tool

### How It Works
The sandbox includes a **Component Selector Tool** that makes rapid iteration incredibly smooth:

1. **Hover over any component** → A white pill appears above it showing the exact class name
2. **Click any component** → Copies the class name to your clipboard (silently, no notifications)
3. **Move to next component** → Pill smoothly transitions to show the new component name

### Example Workflow
```
1. Hover over "Primary CTA" button → See "cta-button" pill above it
2. Click the button → "cta-button" copied to clipboard
3. In new chat: "Make the cta-button have rounded corners"
4. Hover over "Secondary CTA" → See "cta-button2-fixed" pill
5. Click it → "cta-button2-fixed" copied to clipboard
6. In chat: "Change cta-button2-fixed to use a different color"
```

### No Layout Shifts
- **Stable layout** - no jarring screen movements
- **Silent copy** - no notifications that push content around
- **Smooth transitions** - pill appears/disappears smoothly
- **Pure functionality** - just hover, see name, click to copy

## 📋 Component Reference

### Typography
```tsx
// Main headings
<h1 className="section h1">Your Title</h1>          // Hover shows: "section h1"
<h2 className="section h2">Section Title</h2>       // Hover shows: "section h2"
<h3 className="component-title">Component Title</h3> // Hover shows: "component-title"
<h4 className="popup-section h4">Subsection</h4>    // Hover shows: "popup-section h4"

// Body text
<p className="section p">Primary text</p>            // Hover shows: "section p"
<p className="waitlist-header p">Secondary text</p>  // Hover shows: "waitlist-header p"
<p className="stats-source">Tertiary text</p>        // Hover shows: "stats-source"
```

### Buttons
```tsx
// Primary actions
<a href="#" className="cta-button">Primary CTA</a>           // Hover shows: "cta-button"
<a href="#" className="cta-button2-fixed">Secondary CTA</a> // Hover shows: "cta-button2-fixed"
<button className="dpu-btn">Submit</button>                  // Hover shows: "dpu-btn"

// Secondary actions
<button className="stop-button">Stop</button>                // Hover shows: "stop-button"
<button className="add-path-button">Add Path</button>        // Hover shows: "add-path-button"
<button className="info-pill-icon">Info</button>             // Hover shows: "info-pill-icon"
```

### Form Elements
```tsx
// Standard input
<div className="input-wrapper">                              // Hover shows: "input-wrapper"
  <input type="text" placeholder="Enter text" />
</div>

// Input with icon
<div className="popup-input-wrapper">                        // Hover shows: "popup-input-wrapper"
  <img src="/assets/SpaceportIcons/Pin.svg" className="input-icon pin" alt="" />
  <input type="text" placeholder="Address" />
</div>

// Input with suffix
<div className="popup-input-wrapper has-suffix" data-suffix="acres"> // Hover shows: "popup-input-wrapper has-suffix"
  <img src="/assets/SpaceportIcons/Number.svg" className="input-icon number" alt="" />
  <input type="number" placeholder="Size" />
</div>

// Textarea
<div className="popup-input-wrapper listing-description-wrapper"> // Hover shows: "popup-input-wrapper listing-description-wrapper"
  <img src="/assets/SpaceportIcons/Paragraph.svg" className="input-icon paragraph" alt="" />
  <textarea placeholder="Description"></textarea>
</div>

// Select
<label className="step-selector-label">Pipeline Step</label> // Hover shows: "step-selector-label"
<select className="step-selector">                           // Hover shows: "step-selector"
  <option value="sfm">SfM Processing</option>
</select>

// Toggle
<div className="ios-toggle-container">                       // Hover shows: "ios-toggle-container"
  <span>Enable Feature</span>
  <div className="toggle-switch">...</div>
</div>
```

### Cards
```tsx
// Project card
<div className="project-box">                               // Hover shows: "project-box"
  <h1>Project Name</h1>
  <p>Project description</p>
</div>

// New project card
<div className="new-project-card">                          // Hover shows: "new-project-card"
  <h1>+ New Project</h1>
  <div className="plus-icon">...</div>
</div>

// Waitlist card
<div className="waitlist-card">                             // Hover shows: "waitlist-card"
  <div className="waitlist-header">...</div>
</div>
```

### Upload & Progress
```tsx
// Upload zone
<div className="upload-zone">                               // Hover shows: "upload-zone"
  <div className="upload-icon"></div>
  <p>Drag & drop files here</p>
</div>

// Progress bar
<div className="progress-bar">                              // Hover shows: "progress-bar"
  <div className="progress-bar-fill" style={{ width: '65%' }}></div>
</div>

// Spinner
<div className="spinner"></div>                             // Hover shows: "spinner"

// Status indicators
<div className="status-indicator">                          // Hover shows: "status-indicator"
  <div className="status-dot pending"></div>
  <span>Pending</span>
</div>
```

### Modal & Accordion
```tsx
// Modal overlay
<div className="popup-overlay">                             // Hover shows: "popup-overlay"
  <div className="popup-content-scroll">
    <div className="popup-header">                          // Hover shows: "popup-header"
      <div className="popup-title-section">
        <input className="popup-title-input" placeholder="Project Title" /> // Hover shows: "popup-title-input"
      </div>
      <button className="popup-close"></button>              // Hover shows: "popup-close"
    </div>
    
    <div className="accordion-section active">               // Hover shows: "accordion-section"
      <div className="accordion-header">                     // Hover shows: "accordion-header"
        <div className="accordion-title">...</div>
      </div>
      <div className="accordion-content">
        <p className="section-description">...</p>            // Hover shows: "section-description"
        <div className="category-outline">                   // Hover shows: "category-outline"
          <div className="popup-section">                    // Hover shows: "popup-section"
            <div className="input-row-popup">                // Hover shows: "input-row-popup"
              <div className="popup-input-wrapper">...</div> // Hover shows: "popup-input-wrapper"
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

### Map Components
```tsx
// Map wrapper
<div className="map-wrapper">                               // Hover shows: "map-wrapper"
  <div className="map-container">                           // Hover shows: "map-container"
    <div className="map-blur-background"></div>
    <div className="map-instructions-center">               // Hover shows: "map-instructions-center"
      <div className="instruction-content">                 // Hover shows: "instruction-content"
        <div className="instruction-pin"></div>
        <h3>Click to place property marker</h3>
      </div>
    </div>
  </div>
  
  <div className="address-search-overlay">                  // Hover shows: "address-search-overlay"
    <div className="address-search-wrapper">                // Hover shows: "address-search-wrapper"
      <input type="text" placeholder="Search address..." />
    </div>
  </div>
  
  <button className="expand-button">                       // Hover shows: "expand-button"
    <div className="expand-icon"></div>
  </button>
</div>
```

### Progress Tracking
```tsx
// Progress tracker
<div className="apple-progress-tracker">                    // Hover shows: "apple-progress-tracker"
  <div className="progress-container">                      // Hover shows: "progress-container"
    <div className="pill-progress-bar">                     // Hover shows: "pill-progress-bar"
      <div className="pill-progress-fill" style={{ width: '75%' }}></div>
    </div>
    <p className="status-text">Processing 3D model...</p>   // Hover shows: "status-text"
  </div>
  
  <div className="action-buttons">                         // Hover shows: "action-buttons"
    <button className="stop-button">Stop</button>           // Hover shows: "stop-button"
  </div>
</div>
```

### Feedback Messages
```tsx
// Success message
<div className="job-status">                               // Hover shows: "job-status"
  <h3>Processing Complete</h3>
  <p>Your 3D model has been successfully generated.</p>
</div>

// Error message
<div className="error-message">                            // Hover shows: "error-message"
  <h3>Processing Error</h3>
  <p>There was an issue processing your request.</p>
</div>
```

## 🚀 Rapid Iteration Workflow

### For New Chats
1. **Open the sandbox** at `/sandbox`
2. **Hover over components** to see their exact class names
3. **Click to copy** class names to clipboard
4. **Paste in new chat** with your desired changes

### Example Chat Starters
```
"Make the cta-button have rounded corners and a subtle shadow"

"Change the popup-input-wrapper to use a different border color"

"Update the project-box to have more padding and a different background"

"Modify the upload-zone to show a different icon and text"

"Adjust the status-indicator to use different colors for each state"
```

### Benefits
- **Instant component identification** - no hunting through code
- **Exact class names** - no guessing or typos
- **Rapid iteration** - copy, paste, describe changes
- **Stable workflow** - no layout shifts or distractions

## 📱 Responsive Design

### Breakpoints
```css
/* Mobile First */
@media (min-width: 640px) { /* Small tablets */ }
@media (min-width: 768px) { /* Tablets */ }
@media (min-width: 1024px) { /* Laptops */ }
```

### Behavior
- Components stack vertically on mobile
- Expand horizontally on larger screens
- Touch-friendly interactions
- Consistent spacing across devices

## 🎯 Standardization Goals

### Phase 1: Component Audit ✅
- [x] Create focused component showcase
- [x] Document create page components
- [x] Remove unnecessary elements
- [x] Implement component selector tool

### Phase 2: Style Standardization
- [ ] Standardize typography scales
- [ ] Unify spacing system
- [ ] Consistent component patterns
- [ ] Unified button styles

### Phase 3: Implementation
- [ ] Refactor create page to use standardized components
- [ ] Create reusable component library
- [ ] Implement consistent spacing
- [ ] Standardize responsive behavior

## 🚀 Best Practices

### 1. Component Reuse
- Use existing components instead of creating new ones
- Extend components with props rather than duplicating code
- Maintain consistent naming conventions

### 2. Minimalism
- Keep designs clean and uncluttered
- Focus on functionality over decoration
- Use consistent spacing and typography
- Avoid unnecessary animations

### 3. Accessibility
- Maintain proper color contrast
- Use semantic HTML elements
- Provide alternative text for images
- Ensure keyboard navigation works

## 🔍 Testing

### Visual Testing
- [ ] Components render correctly
- [ ] Responsive behavior works
- [ ] Consistent appearance
- [ ] No layout shifts or jarring effects

### Functionality Testing
- [ ] Component selector tool works smoothly
- [ ] Hover shows correct class names
- [ ] Click copies to clipboard
- [ ] No visual distractions or animations

## 📚 Resources

### Development
- **Component Library**: Reusable components
- **Design Tokens**: Consistent values
- **Usage Examples**: Implementation patterns
- **Style Guide**: Visual standards

### Tools
- **ESLint**: Code quality
- **Prettier**: Code formatting
- **Stylelint**: CSS consistency
- **Browser Testing**: Cross-platform validation

## 🤝 Contributing

### Adding Components
1. Add to appropriate section in sandbox
2. Test functionality and appearance
3. Update documentation
4. Ensure consistency with existing patterns

### Updating Components
1. Test changes in sandbox
2. Validate responsive behavior
3. Check accessibility
4. Update documentation

---

**Last Updated**: Design System v1.1
**Focus**: Create page components only
**Style**: Hyper-minimalist, no animations, smooth transitions
**Tool**: Component Selector with hover-to-see, click-to-copy
**Maintained By**: Spaceport Development Team
