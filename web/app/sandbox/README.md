# Spaceport Design System Sandbox

## 🎯 Purpose

This sandbox serves as a minimalist showcase of design components used specifically on the create page. It's designed to help standardize the website design by providing a clean, focused reference for developers.

## 🚀 Getting Started

### Access the Sandbox
Navigate to `/sandbox` in your browser to view the create page components.

### What You'll See
The sandbox is organized into focused sections:

1. **Typography** - Text styles and headings
2. **Buttons** - Primary and secondary actions
3. **Form Elements** - Inputs, selects, toggles
4. **Cards** - Project cards and waitlist
5. **Upload** - Upload zones, progress, status
6. **Modal** - Modal overlays and accordions
7. **Map** - Map containers and search
8. **Progress** - Progress bars and actions
9. **Feedback** - Status messages and errors

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

## 🔧 Component Usage

### Typography
```tsx
// Main headings
<h1 className="section h1">Your Title</h1>
<h2 className="section h2">Section Title</h2>
<h3 className="component-title">Component Title</h3>
<h4 className="popup-section h4">Subsection</h4>

// Body text
<p className="section p">Primary text</p>
<p className="waitlist-header p">Secondary text</p>
<p className="stats-source">Tertiary text</p>
```

### Buttons
```tsx
// Primary actions
<a href="#" className="cta-button">Primary CTA</a>
<a href="#" className="cta-button2-fixed">Secondary CTA</a>
<button className="dpu-btn">Submit</button>

// Secondary actions
<button className="stop-button">Stop</button>
<button className="add-path-button">Add Path</button>
<button className="info-pill-icon">Info</button>
```

### Form Elements
```tsx
// Standard input
<div className="input-wrapper">
  <input type="text" placeholder="Enter text" />
</div>

// Input with icon
<div className="popup-input-wrapper">
  <img src="/assets/SpaceportIcons/Pin.svg" className="input-icon pin" alt="" />
  <input type="text" placeholder="Address" />
</div>

// Input with suffix
<div className="popup-input-wrapper has-suffix" data-suffix="acres">
  <img src="/assets/SpaceportIcons/Number.svg" className="input-icon number" alt="" />
  <input type="number" placeholder="Size" />
</div>

// Textarea
<div className="popup-input-wrapper listing-description-wrapper">
  <img src="/assets/SpaceportIcons/Paragraph.svg" className="input-icon paragraph" alt="" />
  <textarea placeholder="Description"></textarea>
</div>
```

### Cards
```tsx
// Project card
<div className="project-box">
  <h1>Project Name</h1>
  <p>Project description</p>
</div>

// New project card
<div className="new-project-card">
  <h1>+ New Project</h1>
  <div className="plus-icon">
    <span></span>
    <span></span>
  </div>
</div>

// Waitlist card
<div className="waitlist-card">
  <div className="waitlist-header">
    <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport" className="waitlist-logo" />
    <h1>Join the Waitlist</h1>
    <p>Description text</p>
  </div>
</div>
```

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
- [ ] No unnecessary animations

### Functionality Testing
- [ ] Components work as intended
- [ ] Form elements function properly
- [ ] Interactive elements respond correctly
- [ ] Accessibility features work

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

**Last Updated**: Design System v1.0
**Focus**: Create page components only
**Style**: Hyper-minimalist, no animations
**Maintained By**: Spaceport Development Team
