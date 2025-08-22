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
    'h3': 'h3',
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
          <h3 className="h3">Instructions</h3>
          <div className="body-text">
            Double-click on any text below to edit it and see how different content looks in each typography style. Press Enter to save changes or click outside to cancel. Single-click to copy component names.
          </div>
        </div>
        
        <div className="component-group">
          <h3 className="h3">Headings - Largest to Smallest</h3>
          <div className="component-showcase">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', alignItems: 'center' }}>
              <h1 
                className="section h1"
                data-component="section h1"
                onMouseEnter={(e) => handleComponentHover('section h1', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('section h1')}
                onDoubleClick={(e) => handleDoubleClick('section h1', e)}
              >
                section h1
              </h1>
              <h2 
                className="section h2"
                data-component="section h2"
                onMouseEnter={(e) => handleComponentHover('section h2', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('section h2')}
                onDoubleClick={(e) => handleDoubleClick('section h2', e)}
              >
                section h2
              </h2>
              <h3 
                className="h3"
                data-component="h3"
                onMouseEnter={(e) => handleComponentHover('h3', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('h3')}
                onDoubleClick={(e) => handleDoubleClick('h3', e)}
              >
                h3
              </h3>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Body Text Examples</h3>
          <div className="component-showcase">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '600px' }}>
              <div 
                className="body-text"
                data-component="body-text"
                onMouseEnter={(e) => handleComponentHover('body-text', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('body-text')}
                onDoubleClick={(e) => handleDoubleClick('body-text', e)}
              >
                This is an example of our standard body-text class. It demonstrates how regular paragraph text appears in our design system. The text is sized appropriately for comfortable reading and uses our established opacity and spacing guidelines to ensure excellent readability across all devices.
              </div>
              <div 
                className="body-text"
                data-component="body-text with highlights"
                onMouseEnter={(e) => handleComponentHover('body-text with highlights', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('body-text with highlights')}
                onDoubleClick={(e) => handleDoubleClick('body-text with highlights', e)}
              >
                This paragraph shows how <span className="text-highlight">text-highlight</span> works within our body-text class. You can emphasize <span className="text-highlight">key phrases</span> or <span className="text-highlight">important terms</span> to draw attention to specific content. The highlight maintains the same font weight but increases opacity to 100% for better visibility while keeping the text cohesive.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Colors */}
      <section className="sandbox-section">
        <h2 className="section-title">Colors</h2>
        
        <div className="component-group">
          <h3 className="h3">Primary Colors</h3>
          <div className="component-showcase">
            <div 
              className="color-swatch pure-white"
              data-component="pure-white"
              onMouseEnter={(e) => handleComponentHover('pure-white', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('pure-white')}
            >
              Pure White
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Opacity Stops - Against Dark Background</h3>
          <div className="body-text">
            These are our predetermined opacity levels for creating grayscale elements. We never hardcode gray - we use white with specific opacity values.
          </div>
          <div className="component-showcase">
            <div className="color-swatch-container">
              <div 
                className="color-swatch opacity-stop-10"
                data-component="opacity-stop-10"
                onMouseEnter={(e) => handleComponentHover('opacity-stop-10', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('opacity-stop-10')}
              >
                10%
              </div>
              <div 
                className="color-swatch opacity-stop-20"
                data-component="opacity-stop-20"
                onMouseEnter={(e) => handleComponentHover('opacity-stop-20', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('opacity-stop-20')}
              >
                20%
              </div>
              <div 
                className="color-swatch opacity-stop-50"
                data-component="opacity-stop-50"
                onMouseEnter={(e) => handleComponentHover('opacity-stop-50', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('opacity-stop-50')}
              >
                50%
              </div>
              <div 
                className="color-swatch opacity-stop-100"
                data-component="opacity-stop-100"
                onMouseEnter={(e) => handleComponentHover('opacity-stop-100', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('opacity-stop-100')}
              >
                100%
              </div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Opacity Stops - Against Light Background</h3>
          <div className="body-text">
            Same opacity levels, but against a light background to show contrast.
          </div>
          <div className="component-showcase">
            <div className="light-background-container">
              <div 
                className="color-swatch opacity-stop-10-dark"
                data-component="opacity-stop-10-dark"
                onMouseEnter={(e) => handleComponentHover('opacity-stop-10-dark', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('opacity-stop-10-dark')}
              >
                10%
              </div>
              <div 
                className="color-swatch opacity-stop-20-dark"
                data-component="opacity-stop-20-dark"
                onMouseEnter={(e) => handleComponentHover('opacity-stop-20-dark', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('opacity-stop-20-dark')}
              >
                20%
              </div>
              <div 
                className="color-swatch opacity-stop-50-dark"
                data-component="opacity-stop-50-dark"
                onMouseEnter={(e) => handleComponentHover('opacity-stop-50-dark', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('opacity-stop-50-dark')}
              >
                50%
              </div>
              <div 
                className="color-swatch opacity-stop-100-dark"
                data-component="opacity-stop-100-dark"
                onMouseEnter={(e) => handleComponentHover('opacity-stop-100-dark', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('opacity-stop-100-dark')}
              >
                100%
              </div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Spaceport Prism Pattern</h3>
          <div className="body-text">
            This is our signature Spaceport Prism effect using six specific hex codes in a horizontal linear gradient pattern.
          </div>
          <div className="component-showcase">
            <div 
              className="spaceport-prism"
              data-component="spaceport-prism"
              onMouseEnter={(e) => handleComponentHover('spaceport-prism', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('spaceport-prism')}
            >
              <div className="prism-content">
                <div className="h3">Spaceport Prism</div>
                <div className="body-text">
                  #DC9ED8 • #CD70E4 • #D869B3<br />
                  #E4617C • #EB5C5A • #E47991
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Borders */}
      <section className="sandbox-section">
        <h2 className="section-title">Borders</h2>
        
        <div className="component-group">
          <h3 className="h3">Standard Border</h3>
          <div className="body-text">
            Our default border style - 3px solid with subtle transparency. Used for most components.
          </div>
          <div className="component-showcase">
            <div 
              className="standard-border-demo"
              data-component="standard-border-demo"
              onMouseEnter={(e) => handleComponentHover('standard-border-demo', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('standard-border-demo')}
            >
              <h3 className="h3">Standard Border</h3>
              <div className="body-text">This component uses our default 3px solid border with rgba(255, 255, 255, 0.1).</div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Gradient Border</h3>
          <div className="body-text">
            Our premium border style - diagonal gradient edge that highlights important elements.
          </div>
          <div className="component-showcase">
            <div 
              className="gradient-border-demo"
              data-component="gradient-border-demo"
              onMouseEnter={(e) => handleComponentHover('gradient-border-demo', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('gradient-border-demo')}
            >
              <h3 className="h3">Gradient Border</h3>
              <div className="body-text">This component uses our premium diagonal gradient border for highlighting important elements.</div>
            </div>
          </div>
        </div>
      </section>

      {/* Header Typography */}
      <section className="sandbox-section">
        <h2 className="section-title">Header Typography</h2>
        
        <div className="component-group">
          <h3 className="h3">Navigation Elements</h3>
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
          <h3 className="h3">Header Layout Preview</h3>
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
          <h3 className="h3">Primary Actions</h3>
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
          <h3 className="h3">Default Card</h3>
          <div className="component-showcase">
            <div 
              className="default-card"
              data-component="default-card"
              onMouseEnter={(e) => handleComponentHover('default-card', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('default-card')}
            >
              <h3 className="h3">Default Card</h3>
              <div className="body-text">This is our foundation card component with the proper glasmorphic gradient edge border. It follows the style guide specifications exactly.</div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Project Cards</h3>
          <div className="component-showcase">
            <div 
              className="project-box"
              data-component="project-box"
              onMouseEnter={(e) => handleComponentHover('project-box', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('project-box')}
            >
              <h1 className="section h1">Sample Project</h1>
              <div className="body-text">Project description</div>
            </div>
            <div 
              className="new-project-card"
              data-component="new-project-card"
              onMouseEnter={(e) => handleComponentHover('new-project-card', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('new-project-card')}
            >
              <h1 className="section h1">+ New Project</h1>
              <div className="plus-icon">
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Waitlist Card</h3>
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
                <h1 className="section h1">Join the Waitlist</h1>
                <div className="body-text">Be among the first to experience the future of 3D visualization.</div>
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
