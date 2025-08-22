'use client';

import React, { useState } from 'react';
import './sandbox.css';

export default function DesignSystemSandbox(): JSX.Element {
  const [hoveredComponent, setHoveredComponent] = useState<string | null>(null);
  const [hoveredElement, setHoveredElement] = useState<HTMLElement | null>(null);
  
  // Editable text state for live preview
  const [editableTexts, setEditableTexts] = useState({
    'section h1': 'Create Your Space Today',
    'section h2': 'AI-Powered 3D Reconstruction', 
    'h4': 'Processing Options',
    'body-text': 'Transform your real estate photography into immersive 3D experiences that showcase properties in stunning detail.',
    'body-text with highlights': 'Transform your real estate photography into immersive 3D experiences. Our AI-powered pipeline creates stunning Gaussian splat models that bring properties to life with incredible detail and realism.',
    'header-logo': 'Spaceport',
    'nav-link': '3D Reconstruction',
    'toggle-icon': '≡',
    'pill-button': 'Pill Button'
  });

  const updateEditableText = (key: string, value: string) => {
    setEditableTexts(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleDoubleClick = (key: string, event: React.MouseEvent<HTMLElement>) => {
    const element = event.currentTarget;
    element.contentEditable = 'true';
    element.focus();
    
    // Select all text for easy editing
    const range = document.createRange();
    range.selectNodeContents(element);
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);
    
    // Handle save on blur
    const handleBlur = () => {
      element.contentEditable = 'false';
      updateEditableText(key, element.textContent || editableTexts[key]);
      element.removeEventListener('blur', handleBlur);
    };
    
    element.addEventListener('blur', handleBlur);
    
    // Handle save on Enter key
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        element.blur();
      }
    };
    
    element.addEventListener('keydown', handleKeyDown);
    
    // Clean up event listeners when editing is done
    const cleanup = () => {
      element.removeEventListener('keydown', handleKeyDown);
    };
    
    element.addEventListener('blur', cleanup, { once: true });
  };

  const copyComponentName = async (componentName: string) => {
    try {
      await navigator.clipboard.writeText(componentName);
      // Silent copy - no notification to avoid layout shifts
    } catch (err) {
      console.error('Failed to copy component name:', err);
    }
  };

  const handleComponentHover = (componentName: string, event: React.MouseEvent<HTMLElement>) => {
    setHoveredComponent(componentName);
    setHoveredElement(event.currentTarget);
  };

  const handleComponentLeave = () => {
    setHoveredComponent(null);
    setHoveredElement(null);
  };

  const handleComponentClick = (componentName: string) => {
    copyComponentName(componentName);
  };

  return (
    <div className="sandbox-container">
      {/* Header */}
      <section className="sandbox-section">
        <h1 className="sandbox-title">Design System</h1>
        <p className="sandbox-subtitle">Create page components</p>
      </section>

      {/* Typography */}
      <section className="sandbox-section">
        <h2 className="section-title">Typography</h2>
        
        <div className="component-group">
          <h3 className="component-title">Instructions</h3>
          <p className="section p" style={{ color: 'rgba(255, 255, 255, 0.7)', fontStyle: 'italic' }}>
            💡 Double-click on any text below to edit it and see how different content looks in each typography style. 
            Press Enter to save changes or click outside to cancel. Single-click to copy component names.
          </p>
        </div>
        
        <div className="component-group">
          <h3 className="component-title">Headings</h3>
          <div className="component-showcase">
            <h1 
              className="section h1"
              data-component="section h1"
              onMouseEnter={(e) => handleComponentHover('section h1', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('section h1')}
              onDoubleClick={(e) => handleDoubleClick('section h1', e)}
            >
              {editableTexts['section h1']}
            </h1>
            <h2 
              className="section h2"
              data-component="section h2"
              onMouseEnter={(e) => handleComponentHover('section h2', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('section h2')}
              onDoubleClick={(e) => handleDoubleClick('section h2', e)}
            >
              {editableTexts['section h2']}
            </h2>
            <h3 
              className="component-title"
              data-component="component-title"
              onMouseEnter={(e) => handleComponentHover('component-title', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('component-title')}
              onDoubleClick={(e) => handleDoubleClick('component-title', e)}
            >
              {editableTexts['component-title']}
            </h3>
            <h4 
              className="h4"
              data-component="h4"
              onMouseEnter={(e) => handleComponentHover('h4', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('h4')}
              onDoubleClick={(e) => handleDoubleClick('h4', e)}
            >
              {editableTexts['h4']}
            </h4>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Body Text</h3>
          <div className="component-showcase">
            <div 
              className="body-text"
              data-component="body-text"
              onMouseEnter={(e) => handleComponentHover('body-text', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('body-text')}
              onDoubleClick={(e) => handleDoubleClick('body-text', e)}
            >
              {editableTexts['body-text']}
            </div>
            <div 
              className="body-text"
              data-component="body-text with highlights"
              onMouseEnter={(e) => handleComponentHover('body-text with highlights', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('body-text with highlights')}
              onDoubleClick={(e) => handleDoubleClick('body-text with highlights', e)}
            >
              Transform your real estate photography into immersive 3D experiences. Our <span className="text-highlight">AI-powered pipeline</span> creates stunning <span className="text-highlight">Gaussian splat models</span> that bring properties to life with incredible detail and realism.
            </div>
          </div>
        </div>
      </section>

      {/* Header Typography */}
      <section className="sandbox-section">
        <h2 className="section-title">Header Typography</h2>
        
        <div className="component-group">
          <h3 className="component-title">Navigation Elements</h3>
          <div className="component-showcase">
            <div 
              className="header-logo"
              data-component="header-logo"
              onMouseEnter={(e) => handleComponentHover('header-logo', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('header-logo')}
              onDoubleClick={(e) => handleDoubleClick('header-logo', e)}
            >
              {editableTexts['header-logo']}
            </div>
            <div 
              className="nav-link"
              data-component="nav-link"
              onMouseEnter={(e) => handleComponentHover('nav-link', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('nav-link')}
              onDoubleClick={(e) => handleDoubleClick('nav-link', e)}
            >
              {editableTexts['nav-link']}
            </div>
            <div 
              className="toggle-icon"
              data-component="toggle-icon"
              onMouseEnter={(e) => handleComponentHover('toggle-icon', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('toggle-icon')}
              onDoubleClick={(e) => handleDoubleClick('toggle-icon', e)}
            >
              {editableTexts['toggle-icon']}
            </div>
            <div 
              className="pill-button"
              data-component="pill-button"
              onMouseEnter={(e) => handleComponentHover('pill-button', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('pill-button')}
              onDoubleClick={(e) => handleDoubleClick('pill-button', e)}
            >
              {editableTexts['pill-button']}
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Header Layout Preview</h3>
          <div className="component-showcase">
            <div 
              className="header-preview mobile"
              data-component="header-preview mobile"
              onMouseEnter={(e) => handleComponentHover('header-preview mobile', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('header-preview mobile')}
            >
              <div className="h4 pill-button">{editableTexts['header-logo']}</div>
              <div className="h4 pill-button">
                <span></span>
                <span></span>
              </div>
            </div>
            
            <div 
              className="header-preview desktop"
              data-component="header-preview desktop"
              onMouseEnter={(e) => handleComponentHover('header-preview desktop', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('header-preview desktop')}
            >
              <div className="h4 pill-button">{editableTexts['header-logo']}</div>
              <div className="nav-links-preview">
                <span className="h4 pill-button">Pricing</span>
                <span className="h4 pill-button">About</span>
                <span className="h4 pill-button">Create</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Primary Actions */}
      <section className="sandbox-section">
        <h2 className="section-title">Primary Actions</h2>
        
        <div className="component-group">
          <h3 className="component-title">Primary Actions</h3>
          <div className="component-showcase">
            <a 
              href="#"
              className="cta-button"
              data-component="cta-button"
              onMouseEnter={(e) => handleComponentHover('cta-button', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('cta-button')}
            >
              Start 3D Reconstruction
            </a>
            <a 
              href="#"
              className="cta-button2-fixed"
              data-component="cta-button2-fixed"
              onMouseEnter={(e) => handleComponentHover('cta-button2-fixed', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('cta-button2-fixed')}
            >
              View Demo Gallery
            </a>
            <div 
              className="pill-button"
              data-component="pill-button"
              onMouseEnter={(e) => handleComponentHover('pill-button', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('pill-button')}
              onDoubleClick={(e) => handleDoubleClick('pill-button', e)}
            >
              {editableTexts['pill-button']}
            </div>
          </div>
        </div>
      </section>

      {/* Cards */}
      <section className="sandbox-section">
        <h2 className="section-title">Cards</h2>
        
        <div className="component-group">
          <h3 className="component-title">Default Card</h3>
          <div className="component-showcase">
            <div 
              className="default-card"
              data-component="default-card"
              onMouseEnter={(e) => handleComponentHover('default-card', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('default-card')}
            >
              <h3>Default Card</h3>
              <p>This is our foundation card component with the proper glasmorphic gradient edge border. It follows the style guide specifications exactly.</p>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Project Cards</h3>
          <div className="component-showcase">
            <div 
              className="project-box"
              data-component="project-box"
              onMouseEnter={(e) => handleComponentHover('project-box', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('project-box')}
            >
              <h1>Sample Project</h1>
              <p>Project description</p>
            </div>
            <div 
              className="new-project-card"
              data-component="new-project-card"
              onMouseEnter={(e) => handleComponentHover('new-project-card', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('new-project-card')}
            >
              <h1>+ New Project</h1>
              <div className="plus-icon">
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Waitlist Card</h3>
          <div className="component-showcase">
            <div 
              className="waitlist-card"
              data-component="waitlist-card"
              onMouseEnter={(e) => handleComponentHover('waitlist-card', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('waitlist-card')}
            >
              <div className="waitlist-header">
                <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport" className="waitlist-logo" />
                <h1>Join the Waitlist</h1>
                <p>Be among the first to experience the future of 3D visualization.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Component Name Pill - Positioned above hovered element */}
      {hoveredComponent && hoveredElement && (
        <div 
          className="component-name-pill"
          style={{
            position: 'fixed',
            top: hoveredElement.getBoundingClientRect().top - 40,
            left: hoveredElement.getBoundingClientRect().left + (hoveredElement.getBoundingClientRect().width / 2) - 50,
            zIndex: 10000
          }}
        >
          {hoveredComponent}
        </div>
      )}
    </div>
  );
}
