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
    'pill-button': 'Pill Button',
    'pure-white': 'Pure White',
    'hex-dc9ed8': '#DC9ED8',
    'hex-cd70e4': '#CD70E4',
    'hex-d869b3': '#D869B3',
    'hex-e4617c': '#E4617C',
    'hex-eb5c5a': '#EB5C5A',
    'hex-e47991': '#E47991'
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
          <p className="body-text" style={{ textAlign: 'center' }}>
            Double-click on any text below to edit it and see how different content looks in each typography style. 
            Press Enter to save changes or click outside to cancel. Single-click to copy component names.
          </p>
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
            <div className="color-swatch-container">
              <div 
                className="color-swatch pure-white"
                data-component="pure-white"
                onMouseEnter={(e) => handleComponentHover('pure-white', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('pure-white')}
              >
                Pure White
              </div>
              <div 
                className="color-swatch hex-dc9ed8"
                data-component="hex-dc9ed8"
                onMouseEnter={(e) => handleComponentHover('hex-dc9ed8', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('hex-dc9ed8')}
              >
                #DC9ED8
              </div>
              <div 
                className="color-swatch hex-cd70e4"
                data-component="hex-cd70e4"
                onMouseEnter={(e) => handleComponentHover('hex-cd70e4', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('hex-cd70e4')}
              >
                #CD70E4
              </div>
              <div 
                className="color-swatch hex-d869b3"
                data-component="hex-d869b3"
                onMouseEnter={(e) => handleComponentHover('hex-d869b3', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('hex-d869b3')}
              >
                #D869B3
              </div>
              <div 
                className="color-swatch hex-e4617c"
                data-component="hex-e4617c"
                onMouseEnter={(e) => handleComponentHover('hex-e4617c', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('hex-e4617c')}
              >
                #E4617C
              </div>
              <div 
                className="color-swatch hex-eb5c5a"
                data-component="hex-eb5c5a"
                onMouseEnter={(e) => handleComponentHover('hex-eb5c5a', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('hex-eb5c5a')}
              >
                #EB5C5A
              </div>
              <div 
                className="color-swatch hex-e47991"
                data-component="hex-e47991"
                onMouseEnter={(e) => handleComponentHover('hex-e47991', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('hex-e47991')}
              >
                #E47991
              </div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Opacity Stops - Against Dark Background</h3>
          <p className="body-text" style={{ textAlign: 'center' }}>
            These are our predetermined opacity levels for creating grayscale elements. We never hardcode gray - we use white with specific opacity values.
          </p>
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
          <p className="body-text" style={{ textAlign: 'center' }}>
            Same opacity levels, but against a light background to show contrast.
          </p>
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
          <p className="body-text" style={{ textAlign: 'center' }}>
            This is our signature Spaceport Prism effect using six specific hex codes in a horizontal linear gradient pattern.
          </p>
          <div className="component-showcase">
            <div className="color-swatch-container">
              <div 
                className="color-swatch hex-dc9ed8"
                data-component="hex-dc9ed8"
                onMouseEnter={(e) => handleComponentHover('hex-dc9ed8', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('hex-dc9ed8')}
              >
                #DC9ED8
              </div>
              <div 
                className="color-swatch hex-cd70e4"
                data-component="hex-cd70e4"
                onMouseEnter={(e) => handleComponentHover('hex-cd70e4', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('hex-cd70e4')}
              >
                #CD70E4
              </div>
              <div 
                className="color-swatch hex-d869b3"
                data-component="hex-d869b3"
                onMouseEnter={(e) => handleComponentHover('hex-d869b3', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('hex-d869b3')}
              >
                #D869B3
              </div>
              <div 
                className="color-swatch hex-e4617c"
                data-component="hex-e4617c"
                onMouseEnter={(e) => handleComponentHover('hex-e4617c', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('hex-e4617c')}
              >
                #E4617C
              </div>
              <div 
                className="color-swatch hex-eb5c5a"
                data-component="hex-eb5c5a"
                onMouseEnter={(e) => handleComponentHover('hex-eb5c5a', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('hex-eb5c5a')}
              >
                #EB5C5A
              </div>
              <div 
                className="color-swatch hex-e47991"
                data-component="hex-e47991"
                onMouseEnter={(e) => handleComponentHover('hex-e47991', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('hex-e47991')}
              >
                #E47991
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
          <p className="body-text" style={{ textAlign: 'center' }}>
            Our default border style - 3px solid with subtle transparency. Used for most components.
          </p>
          <div className="component-showcase">
            <div 
              className="standard-border-demo"
              data-component="standard-border-demo"
              onMouseEnter={(e) => handleComponentHover('standard-border-demo', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('standard-border-demo')}
            >
                             <h3 className="h3">Standard Border</h3>
               <p className="body-text">This component uses our default 3px solid border with rgba(255, 255, 255, 0.1).</p>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Gradient Border</h3>
          <p className="body-text" style={{ textAlign: 'center' }}>
            Our premium border style - diagonal gradient edge that highlights important elements.
          </p>
          <div className="component-showcase">
            <div 
              className="gradient-border-demo"
              data-component="gradient-border-demo"
              onMouseEnter={(e) => handleComponentHover('gradient-border-demo', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('gradient-border-demo')}
            >
                             <h3 className="h3">Gradient Border</h3>
               <p className="body-text">This component uses our premium diagonal gradient border for highlighting important elements.</p>
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
               <p className="body-text">This is our foundation card component with the proper glasmorphic gradient edge border. It follows the style guide specifications exactly.</p>
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
               <p className="body-text">Project description</p>
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
                 <p className="body-text">Be among the future of 3D visualization.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* New Project Popup Components */}
      <section className="sandbox-section">
        <h2 className="section-title">New Project Popup Components</h2>
        
        <div className="component-group">
          <h3 className="h3">Popup Overlay & Header</h3>
          <div className="component-showcase">
            <div 
              className="popup-overlay"
              data-component="popup-overlay"
              onMouseEnter={(e) => handleComponentHover('popup-overlay', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('popup-overlay')}
              style={{ position: 'relative', height: '200px', display: 'block' }}
            >
              <div 
                className="popup-header"
                data-component="popup-header"
                onMouseEnter={(e) => handleComponentHover('popup-header', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('popup-header')}
              >
                <div 
                  className="popup-title-section"
                  data-component="popup-title-section"
                  onMouseEnter={(e) => handleComponentHover('popup-title-section', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('popup-title-section')}
                >
                  <textarea
                    className="popup-title-input"
                    data-component="popup-title-input"
                    onMouseEnter={(e) => handleComponentHover('popup-title-input', e)}
                    onMouseLeave={handleComponentLeave}
                    onClick={() => handleComponentClick('popup-title-input')}
                    rows={1}
                    placeholder="Untitled"
                    defaultValue="Sample Project"
                  />
                  <span 
                    className="edit-icon"
                    data-component="edit-icon"
                    onMouseEnter={(e) => handleComponentHover('edit-icon', e)}
                    onMouseLeave={handleComponentLeave}
                    onClick={() => handleComponentClick('edit-icon')}
                  />
                </div>
                <button 
                  className="popup-close"
                  data-component="popup-close"
                  onMouseEnter={(e) => handleComponentHover('popup-close', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('popup-close')}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Accordion Sections</h3>
          <div className="component-showcase">
            <div 
              className="accordion-section active"
              data-component="accordion-section"
              onMouseEnter={(e) => handleComponentHover('accordion-section', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('accordion-section')}
            >
              <div 
                className="accordion-header"
                data-component="accordion-header"
                onMouseEnter={(e) => handleComponentHover('accordion-header', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('accordion-header')}
              >
                <div 
                  className="accordion-title"
                  data-component="accordion-title"
                  onMouseEnter={(e) => handleComponentHover('accordion-title', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('accordion-title')}
                >
                  <h3>Create Flight Plan</h3>
                </div>
                <span 
                  className="accordion-chevron"
                  data-component="accordion-chevron"
                  onMouseEnter={(e) => handleComponentHover('accordion-chevron', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('accordion-chevron')}
                />
              </div>
              <div 
                className="accordion-content"
                data-component="accordion-content"
                onMouseEnter={(e) => handleComponentHover('accordion-content', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('accordion-content')}
                style={{ maxHeight: '200px', opacity: 1 }}
              >
                <div 
                  className="category-outline"
                  data-component="category-outline"
                  onMouseEnter={(e) => handleComponentHover('category-outline', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('category-outline')}
                >
                  <div 
                    className="popup-section"
                    data-component="popup-section"
                    onMouseEnter={(e) => handleComponentHover('popup-section', e)}
                    onMouseLeave={handleComponentLeave}
                    onClick={() => handleComponentClick('popup-section')}
                  >
                    <h4>Batteries</h4>
                    <div 
                      className="input-row-popup"
                      data-component="input-row-popup"
                      onMouseEnter={(e) => handleComponentHover('input-row-popup', e)}
                      onMouseLeave={handleComponentLeave}
                      onClick={() => handleComponentClick('input-row-popup')}
                    >
                      <div 
                        className="popup-input-wrapper"
                        data-component="popup-input-wrapper"
                        onMouseEnter={(e) => handleComponentHover('popup-input-wrapper', e)}
                        onMouseLeave={handleComponentLeave}
                        onClick={() => handleComponentClick('popup-input-wrapper')}
                      >
                        <span 
                          className="input-icon time"
                          data-component="input-icon"
                          onMouseEnter={(e) => handleComponentHover('input-icon', e)}
                          onMouseLeave={handleComponentLeave}
                          onClick={() => handleComponentClick('input-icon')}
                        />
                        <input
                          type="text"
                          className="text-fade-right"
                          placeholder="Duration"
                          defaultValue="30 min/battery"
                          data-component="popup-input"
                          onMouseEnter={(e) => handleComponentHover('popup-input', e)}
                          onMouseLeave={handleComponentLeave}
                          onClick={() => handleComponentClick('popup-input')}
                        />
                      </div>
                      <div 
                        className="popup-input-wrapper"
                        data-component="popup-input-wrapper"
                        onMouseEnter={(e) => handleComponentHover('popup-input-wrapper', e)}
                        onMouseLeave={handleComponentLeave}
                        onClick={() => handleComponentClick('popup-input-wrapper')}
                      >
                        <span 
                          className="input-icon number"
                          data-component="input-icon"
                          onMouseEnter={(e) => handleComponentHover('input-icon', e)}
                          onMouseLeave={handleComponentLeave}
                          onClick={() => handleComponentClick('input-icon')}
                        />
                        <input
                          type="text"
                          className="text-fade-right"
                          placeholder="Quantity"
                          defaultValue="2 batteries"
                          data-component="popup-input"
                          onMouseEnter={(e) => handleComponentHover('popup-input', e)}
                          onMouseLeave={handleComponentLeave}
                          onClick={() => handleComponentClick('popup-input')}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Flight Path Download Buttons</h3>
          <div className="component-showcase">
            <div 
              className="flight-path-grid"
              data-component="flight-path-grid"
              onMouseEnter={(e) => handleComponentHover('flight-path-grid', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('flight-path-grid')}
            >
              <button
                className="flight-path-download-btn"
                data-component="flight-path-download-btn"
                onMouseEnter={(e) => handleComponentHover('flight-path-download-btn', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('flight-path-download-btn')}
                style={{ opacity: 1, transform: 'translateY(0) scale(1)' }}
              >
                <span 
                  className="download-icon"
                  data-component="download-icon"
                  onMouseEnter={(e) => handleComponentHover('download-icon', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('download-icon')}
                />
                Battery 1
              </button>
              <button
                className="flight-path-download-btn"
                data-component="flight-path-download-btn"
                onMouseEnter={(e) => handleComponentHover('flight-path-download-btn', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('flight-path-download-btn')}
                style={{ opacity: 1, transform: 'translateY(0) scale(1)' }}
              >
                <span 
                  className="download-icon"
                  data-component="download-icon"
                  onMouseEnter={(e) => handleComponentHover('download-icon', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('download-icon')}
                />
                Battery 2
              </button>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Upload Components</h3>
          <div className="component-showcase">
            <div 
              className="upload-zone"
              data-component="upload-zone"
              onMouseEnter={(e) => handleComponentHover('upload-zone', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('upload-zone')}
            >
              <div 
                className="upload-icon"
                data-component="upload-icon"
                onMouseEnter={(e) => handleComponentHover('upload-icon', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('upload-icon')}
              />
              <p>Upload .jpg photos as a .zip file</p>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Upload Buttons</h3>
          <div className="component-showcase">
            <div 
              className="upload-button-container"
              data-component="upload-button-container"
              onMouseEnter={(e) => handleComponentHover('upload-button-container', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('upload-button-container')}
              style={{ position: 'relative', height: '50px' }}
            >
              <button 
                className="upload-btn-with-icon"
                data-component="upload-btn-with-icon"
                onMouseEnter={(e) => handleComponentHover('upload-btn-with-icon', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('upload-btn-with-icon')}
                style={{ position: 'relative', top: 'auto', left: 'auto', transform: 'none' }}
              >
                <span 
                  className="upload-btn-icon"
                  data-component="upload-btn-icon"
                  onMouseEnter={(e) => handleComponentHover('upload-btn-icon', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('upload-btn-icon')}
                />
                Upload
              </button>
              <button 
                className="cancel-btn-with-icon"
                data-component="cancel-btn-with-icon"
                onMouseEnter={(e) => handleComponentHover('cancel-btn-with-icon', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('cancel-btn-with-icon')}
                style={{ position: 'relative', top: 'auto', left: 'auto', transform: 'none', opacity: 1, color: '#111' }}
              >
                <span 
                  className="cancel-btn-icon"
                  data-component="cancel-btn-icon"
                  onMouseEnter={(e) => handleComponentHover('cancel-btn-icon', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('cancel-btn-icon')}
                />
                Cancel
              </button>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Address Search Overlay</h3>
          <div className="component-showcase">
            <div 
              className="address-search-overlay"
              data-component="address-search-overlay"
              onMouseEnter={(e) => handleComponentHover('address-search-overlay', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('address-search-overlay')}
              style={{ position: 'relative', bottom: 'auto', left: 'auto', right: 'auto' }}
            >
              <div 
                className="address-search-wrapper"
                data-component="address-search-wrapper"
                onMouseEnter={(e) => handleComponentHover('address-search-wrapper', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('address-search-wrapper')}
              >
                <input
                  type="text"
                  className="text-fade-right"
                  placeholder="Enter location"
                  defaultValue="123 Main St, City, State"
                  data-component="address-search-input"
                  onMouseEnter={(e) => handleComponentHover('address-search-input', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('address-search-input')}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Map Controls</h3>
          <div className="component-showcase">
            <button 
              className="expand-button"
              data-component="expand-button"
              onMouseEnter={(e) => handleComponentHover('expand-button', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('expand-button')}
              style={{ position: 'relative', top: 'auto', right: 'auto' }}
            >
              <span 
                className="expand-icon"
                data-component="expand-icon"
                onMouseEnter={(e) => handleComponentHover('expand-icon', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('expand-icon')}
              />
            </button>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Text Area Input</h3>
          <div className="component-showcase">
            <div 
              className="popup-input-wrapper listing-description-wrapper"
              data-component="popup-input-wrapper listing-description-wrapper"
              onMouseEnter={(e) => handleComponentHover('popup-input-wrapper listing-description-wrapper', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('popup-input-wrapper listing-description-wrapper')}
            >
              <span 
                className="input-icon paragraph"
                data-component="input-icon paragraph"
                onMouseEnter={(e) => handleComponentHover('input-icon paragraph', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('input-icon paragraph')}
              />
              <textarea
                className="text-fade-right"
                placeholder="Listing Description"
                rows={3}
                defaultValue="Beautiful property with stunning views..."
                data-component="popup-textarea"
                onMouseEnter={(e) => handleComponentHover('popup-textarea', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('popup-textarea')}
              />
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Modal Popup System</h3>
          <div className="component-showcase">
            <div 
              className="modal-popup-overlay"
              data-component="modal-popup-overlay"
              onMouseEnter={(e) => handleComponentHover('modal-popup-overlay', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('modal-popup-overlay')}
              style={{ position: 'relative', display: 'block' }}
            >
              <div 
                className="modal-popup-content"
                data-component="modal-popup-content"
                onMouseEnter={(e) => handleComponentHover('modal-popup-content', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('modal-popup-content')}
              >
                <div 
                  className="modal-popup-icon success"
                  data-component="modal-popup-icon"
                  onMouseEnter={(e) => handleComponentHover('modal-popup-icon', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('modal-popup-icon')}
                >
                  ✓
                </div>
                <h3 
                  className="modal-popup-title"
                  data-component="modal-popup-title"
                  onMouseEnter={(e) => handleComponentHover('modal-popup-title', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('modal-popup-title')}
                >
                  Success
                </h3>
                <p 
                  className="modal-popup-message"
                  data-component="modal-popup-message"
                  onMouseEnter={(e) => handleComponentHover('modal-popup-message', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('modal-popup-message')}
                >
                  Your project has been saved successfully.
                </p>
                <button 
                  className="modal-popup-button"
                  data-component="modal-popup-button"
                  onMouseEnter={(e) => handleComponentHover('modal-popup-button', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('modal-popup-button')}
                >
                  OK
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Dashboard Project Cards */}
      <section className="sandbox-section">
        <h2 className="section-title">Dashboard Project Cards</h2>
        
        <div className="component-group">
          <h3 className="h3">Project Cards Container</h3>
          <div className="component-showcase">
            <div 
              className="project-cards"
              data-component="project-cards"
              onMouseEnter={(e) => handleComponentHover('project-cards', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('project-cards')}
              style={{ flexDirection: 'row', flexWrap: 'wrap', gap: '20px', justifyContent: 'center' }}
            >
              <div 
                className="project-box"
                data-component="project-box"
                onMouseEnter={(e) => handleComponentHover('project-box', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('project-box')}
                style={{ flex: '0 0 calc(50% - 10px)', width: 'calc(50% - 10px)' }}
              >
                <button 
                  className="project-controls-btn"
                  data-component="project-controls-btn"
                  onMouseEnter={(e) => handleComponentHover('project-controls-btn', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('project-controls-btn')}
                >
                  <img 
                    src="/assets/SpaceportIcons/Controls.svg" 
                    className="project-controls-icon" 
                    alt="Edit controls"
                    data-component="project-controls-icon"
                    onMouseEnter={(e) => handleComponentHover('project-controls-icon', e)}
                    onMouseLeave={handleComponentLeave}
                    onClick={() => handleComponentClick('project-controls-icon')}
                  />
                </button>
                <h1>Downtown Property</h1>
                <p>Processing - Neural network training in progress.</p>
                <div style={{marginTop:12}}>
                  <div style={{height:6, borderRadius:3, background:'rgba(255,255,255,0.1)'}}>
                    <div style={{height:6, borderRadius:3, width:'75%', background:'#fff'}}></div>
                  </div>
                </div>
              </div>
              <div 
                className="project-box"
                data-component="project-box"
                onMouseEnter={(e) => handleComponentHover('project-box', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('project-box')}
                style={{ flex: '0 0 calc(50% - 10px)', width: 'calc(50% - 10px)' }}
              >
                <button 
                  className="project-controls-btn"
                  data-component="project-controls-btn"
                  onMouseEnter={(e) => handleComponentHover('project-controls-btn', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('project-controls-btn')}
                >
                  <img 
                    src="/assets/SpaceportIcons/Controls.svg" 
                    className="project-controls-icon" 
                    alt="Edit controls"
                    data-component="project-controls-icon"
                    onMouseEnter={(e) => handleComponentHover('project-controls-icon', e)}
                    onMouseLeave={handleComponentLeave}
                    onClick={() => handleComponentClick('project-controls-icon')}
                  />
                </button>
                <h1>Lakeside Home</h1>
                <p>Complete - Ready for deployment.</p>
                <div style={{marginTop:12}}>
                  <div style={{height:6, borderRadius:3, background:'rgba(255,255,255,0.1)'}}>
                    <div style={{height:6, borderRadius:3, width:'100%', background:'#fff'}}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Account Card</h3>
          <div className="component-showcase">
            <div 
              className="project-box account-card"
              data-component="account-card"
              onMouseEnter={(e) => handleComponentHover('account-card', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('account-card')}
              style={{ height: '50px', width: '100%' }}
            >
              <div 
                className="account-info"
                data-component="account-info"
                onMouseEnter={(e) => handleComponentHover('account-info', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('account-info')}
              >
                <div 
                  className="account-details"
                  data-component="account-details"
                  onMouseEnter={(e) => handleComponentHover('account-details', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('account-details')}
                >
                  <div 
                    className="account-header"
                    data-component="account-header"
                    onMouseEnter={(e) => handleComponentHover('account-header', e)}
                    onMouseLeave={handleComponentLeave}
                    onClick={() => handleComponentClick('account-header')}
                  >
                    <h3 
                      className="account-handle"
                      data-component="account-handle"
                      onMouseEnter={(e) => handleComponentHover('account-handle', e)}
                      onMouseLeave={handleComponentLeave}
                      onClick={() => handleComponentClick('account-handle')}
                    >
                      SampleUser
                    </h3>
                    <button 
                      className="subscription-pill clickable"
                      data-component="subscription-pill"
                      onMouseEnter={(e) => handleComponentHover('subscription-pill', e)}
                      onMouseLeave={handleComponentLeave}
                      onClick={() => handleComponentClick('subscription-pill')}
                    >
                      Beta Plan
                    </button>
                  </div>
                </div>
                <button 
                  className="sign-out-btn"
                  data-component="sign-out-btn"
                  onMouseEnter={(e) => handleComponentHover('sign-out-btn', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('sign-out-btn')}
                >
                  <span 
                    className="sign-out-icon"
                    data-component="sign-out-icon"
                    onMouseEnter={(e) => handleComponentHover('sign-out-icon', e)}
                    onMouseLeave={handleComponentLeave}
                    onClick={() => handleComponentClick('sign-out-icon')}
                  />
                  Sign Out
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">New Project Card</h3>
          <div className="component-showcase">
            <div 
              className="project-box new-project-card"
              data-component="new-project-card"
              onMouseEnter={(e) => handleComponentHover('new-project-card', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('new-project-card')}
              style={{ width: '100%' }}
            >
              <h1>
                New Project
                <span 
                  className="plus-icon"
                  data-component="plus-icon"
                  onMouseEnter={(e) => handleComponentHover('plus-icon', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('plus-icon')}
                >
                  <span></span>
                  <span></span>
                </span>
              </h1>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Loading Card</h3>
          <div className="component-showcase">
            <div 
              className="project-box loading-card"
              data-component="loading-card"
              onMouseEnter={(e) => handleComponentHover('loading-card', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('loading-card')}
            >
              <div 
                className="loading-spinner"
                data-component="loading-spinner"
                onMouseEnter={(e) => handleComponentHover('loading-spinner', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('loading-spinner')}
              >
                <div 
                  className="spinner"
                  data-component="spinner"
                  onMouseEnter={(e) => handleComponentHover('spinner', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('spinner')}
                />
                <p>Loading projects...</p>
              </div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Project Card with Progress</h3>
          <div className="component-showcase">
            <div 
              className="project-box"
              data-component="project-box"
              onMouseEnter={(e) => handleComponentHover('project-box', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('project-box')}
            >
              <button 
                className="project-controls-btn"
                data-component="project-controls-btn"
                onMouseEnter={(e) => handleComponentHover('project-controls-btn', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('project-controls-btn')}
              >
                <img 
                  src="/assets/SpaceportIcons/Controls.svg" 
                  className="project-controls-icon" 
                  alt="Edit controls"
                  data-component="project-controls-icon"
                  onMouseEnter={(e) => handleComponentHover('project-controls-icon', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('project-controls-icon')}
                />
              </button>
              <h1>Mountain View Estate</h1>
              <p>Processing - Structure from Motion in progress.</p>
              <div style={{marginTop:12}}>
                <div style={{height:6, borderRadius:3, background:'rgba(255,255,255,0.1)'}}>
                  <div style={{height:6, borderRadius:3, width:'45%', background:'#fff'}}></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="h3">Completed Project Card</h3>
          <div className="component-showcase">
            <div 
              className="project-box"
              data-component="project-box"
              onMouseEnter={(e) => handleComponentHover('project-box', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('project-box')}
            >
              <button 
                className="project-controls-btn"
                data-component="project-controls-btn"
                onMouseEnter={(e) => handleComponentHover('project-controls-btn', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('project-controls-btn')}
              >
                <img 
                  src="/assets/SpaceportIcons/Controls.svg" 
                  className="project-controls-icon" 
                  alt="Edit controls"
                  data-component="project-controls-icon"
                  onMouseEnter={(e) => handleComponentHover('project-controls-icon', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('project-controls-icon')}
                />
              </button>
              <h1>Historic Courthouse</h1>
              <p>Complete - Hosting at spaceport.ai</p>
              <div style={{marginTop:12}}>
                <div style={{height:6, borderRadius:3, background:'rgba(255,255,255,0.1)'}}>
                  <div style={{height:6, borderRadius:3, width:'100%', background:'#fff'}}></div>
                </div>
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
