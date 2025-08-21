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
            <h3 
              className="h4"
              data-component="h4"
              onMouseEnter={(e) => handleComponentHover('h4', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('h4')}
              onDoubleClick={(e) => handleDoubleClick('h4', e)}
            >
              {editableTexts['h4']}
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
              Transform your <span className="text-highlight">real estate photography</span> into immersive 3D experiences. Our AI-powered pipeline creates stunning <span className="text-highlight">Gaussian splat models</span> that bring properties to life with incredible detail and realism.
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

      {/* Buttons */}
      <section className="sandbox-section">
        <h2 className="section-title">Buttons</h2>
        
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
            <button 
              className="dpu-btn"
              data-component="dpu-btn"
              onMouseEnter={(e) => handleComponentHover('dpu-btn', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('dpu-btn')}
            >
              Upload Images
            </button>
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
          <h3 className="component-title">Secondary Actions</h3>
          <div className="component-showcase">
            <button 
              className="stop-button"
              data-component="stop-button"
              onMouseEnter={(e) => handleComponentHover('stop-button', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('stop-button')}
            >
              Cancel Processing
            </button>
            <button 
              className="add-path-button"
              data-component="add-path-button"
              onMouseEnter={(e) => handleComponentHover('add-path-button', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('add-path-button')}
            >
              Add Flight Path
            </button>
            <button 
              className="info-pill-icon"
              data-component="info-pill-icon"
              onMouseEnter={(e) => handleComponentHover('info-pill-icon', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('info-pill-icon')}
            >
              Learn More
            </button>
          </div>
        </div>
      </section>

      {/* Form Elements */}
      <section className="sandbox-section">
        <h2 className="section-title">Form Elements</h2>
        
        <div className="component-group">
          <h3 className="component-title">Inputs</h3>
          <div className="component-showcase">
            <div 
              className="input-wrapper"
              data-component="input-wrapper"
              onMouseEnter={(e) => handleComponentHover('input-wrapper', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('input-wrapper')}
            >
              <input type="text" placeholder="Standard input" />
            </div>
            <div 
              className="popup-input-wrapper"
              data-component="popup-input-wrapper"
              onMouseEnter={(e) => handleComponentHover('popup-input-wrapper', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('popup-input-wrapper')}
            >
              <img src="/assets/SpaceportIcons/Pin.svg" className="input-icon pin" alt="" />
              <input type="text" placeholder="Input with icon" />
            </div>
            <div 
              className="popup-input-wrapper has-suffix"
              data-component="popup-input-wrapper has-suffix"
              data-suffix="acres"
              onMouseEnter={(e) => handleComponentHover('popup-input-wrapper has-suffix', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('popup-input-wrapper has-suffix')}
            >
              <img src="/assets/SpaceportIcons/Number.svg" className="input-icon number" alt="" />
              <input type="number" placeholder="Input with suffix" />
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Textarea</h3>
          <div className="component-showcase">
            <div 
              className="popup-input-wrapper listing-description-wrapper"
              data-component="popup-input-wrapper listing-description-wrapper"
              onMouseEnter={(e) => handleComponentHover('popup-input-wrapper listing-description-wrapper', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('popup-input-wrapper listing-description-wrapper')}
            >
              <img src="/assets/SpaceportIcons/Paragraph.svg" className="input-icon paragraph" alt="" />
              <textarea placeholder="Multi-line input"></textarea>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Select</h3>
          <div className="component-showcase">
            <label 
              className="step-selector-label"
              data-component="step-selector-label"
              onMouseEnter={(e) => handleComponentHover('step-selector-label', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('step-selector-label')}
            >
              Pipeline Step
            </label>
            <select 
              className="step-selector"
              data-component="step-selector"
              onMouseEnter={(e) => handleComponentHover('step-selector', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('step-selector')}
            >
              <option value="sfm">SfM Processing</option>
              <option value="3dgs">3D Gaussian Splatting</option>
              <option value="compression">Compression</option>
            </select>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Toggle</h3>
          <div className="component-showcase">
            <div 
              className="ios-toggle-container"
              data-component="ios-toggle-container"
              onMouseEnter={(e) => handleComponentHover('ios-toggle-container', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('ios-toggle-container')}
            >
              <span>Enable Feature</span>
              <div className="toggle-switch">
                <input type="checkbox" id="toggle1" />
                <label htmlFor="toggle1" className="slider"></label>
              </div>
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

      {/* Upload */}
      <section className="sandbox-section">
        <h2 className="section-title">Upload</h2>
        
        <div className="component-group">
          <h3 className="component-title">Upload Zone</h3>
          <div className="component-showcase">
            <div 
              className="upload-zone"
              data-component="upload-zone"
              onMouseEnter={(e) => handleComponentHover('upload-zone', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('upload-zone')}
            >
              <div className="upload-icon"></div>
              <p>Drag & drop files here</p>
              <p className="upload-hint">or click to browse</p>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Progress</h3>
          <div className="component-showcase">
            <div 
              className="progress-bar"
              data-component="progress-bar"
              onMouseEnter={(e) => handleComponentHover('progress-bar', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('progress-bar')}
            >
              <div className="progress-bar-fill" style={{ width: '65%' }}></div>
            </div>
            <div 
              className="spinner"
              data-component="spinner"
              onMouseEnter={(e) => handleComponentHover('spinner', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('spinner')}
            ></div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Status</h3>
          <div className="component-showcase">
            <div 
              className="status-indicator"
              data-component="status-indicator"
              onMouseEnter={(e) => handleComponentHover('status-indicator', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('status-indicator')}
            >
              <div className="status-dot pending"></div>
              <span>Pending</span>
            </div>
            <div 
              className="status-indicator"
              data-component="status-indicator"
              onMouseEnter={(e) => handleComponentHover('status-indicator', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('status-indicator')}
            >
              <div className="status-dot processing"></div>
              <span>Processing</span>
            </div>
            <div 
              className="status-indicator"
              data-component="status-indicator"
              onMouseEnter={(e) => handleComponentHover('status-indicator', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('status-indicator')}
            >
              <div className="status-dot complete"></div>
              <span>Complete</span>
            </div>
          </div>
        </div>
      </section>

      {/* Modal */}
      <section className="sandbox-section">
        <h2 className="section-title">Modal</h2>
        
        <div className="component-group">
          <h3 className="component-title">Modal Overlay</h3>
          <div className="component-showcase">
            <div 
              className="popup-overlay"
              data-component="popup-overlay"
              style={{ position: 'relative', height: '300px' }}
              onMouseEnter={(e) => handleComponentHover('popup-overlay', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('popup-overlay')}
            >
              <div className="popup-content-scroll">
                <div 
                  className="popup-header"
                  data-component="popup-header"
                  onMouseEnter={(e) => handleComponentHover('popup-header', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('popup-header')}
                >
                  <div className="popup-title-section">
                    <input 
                      className="popup-title-input" 
                      placeholder="Project Title"
                      data-component="popup-title-input"
                      onMouseEnter={(e) => handleComponentHover('popup-title-input', e)}
                      onMouseLeave={handleComponentLeave}
                      onClick={() => handleComponentClick('popup-title-input')}
                    />
                  </div>
                  <button 
                    className="popup-close"
                    data-component="popup-close"
                    onMouseEnter={(e) => handleComponentHover('popup-close', e)}
                    onMouseLeave={handleComponentLeave}
                    onClick={() => handleComponentClick('popup-close')}
                  ></button>
                </div>
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
                    <div className="accordion-title">
                      <h3>Property Details</h3>
                    </div>
                    <div className="accordion-chevron"></div>
                  </div>
                  <div className="accordion-content">
                    <p 
                      className="section-description"
                      data-component="section-description"
                      onMouseEnter={(e) => handleComponentHover('section-description', e)}
                      onMouseLeave={handleComponentLeave}
                      onClick={() => handleComponentClick('section-description')}
                    >
                      Enter the basic details about your property.
                    </p>
                    <div 
                      className="category-outline"
                      data-component="category-outline"
                      onMouseEnter={(e) => handleComponentHover('category-outline', e)}
                      onMouseLeave={handleComponentLeave}
                      onClick={() => handleComponentClick('category-outline')}
                    >
                      <h4>Basic Information</h4>
                      <div 
                        className="popup-section"
                        data-component="popup-section"
                        onMouseEnter={(e) => handleComponentHover('popup-section', e)}
                        onMouseLeave={handleComponentLeave}
                        onClick={() => handleComponentClick('popup-section')}
                      >
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
                            <img src="/assets/SpaceportIcons/Pin.svg" className="input-icon pin" alt="" />
                            <input type="text" placeholder="Address" />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Map */}
      <section className="sandbox-section">
        <h2 className="section-title">Map</h2>
        
        <div className="component-group">
          <h3 className="component-title">Map Container</h3>
          <div className="component-showcase">
            <div 
              className="map-wrapper"
              data-component="map-wrapper"
              onMouseEnter={(e) => handleComponentHover('map-wrapper', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('map-wrapper')}
            >
              <div 
                className="map-container"
                data-component="map-container"
                onMouseEnter={(e) => handleComponentHover('map-container', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('map-container')}
              >
                <div className="map-blur-background"></div>
                <div 
                  className="map-instructions-center"
                  data-component="map-instructions-center"
                  onMouseEnter={(e) => handleComponentHover('map-instructions-center', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('map-instructions-center')}
                >
                  <div 
                    className="instruction-content"
                    data-component="instruction-content"
                    onMouseEnter={(e) => handleComponentHover('instruction-content', e)}
                    onMouseLeave={handleComponentLeave}
                    onClick={() => handleComponentClick('instruction-content')}
                  >
                    <div className="instruction-pin"></div>
                    <h3>Click to place property marker</h3>
                  </div>
                </div>
              </div>
              <div 
                className="address-search-overlay"
                data-component="address-search-overlay"
                onMouseEnter={(e) => handleComponentHover('address-search-overlay', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('address-search-overlay')}
              >
                <div 
                  className="address-search-wrapper"
                  data-component="address-search-wrapper"
                  onMouseEnter={(e) => handleComponentHover('address-search-wrapper', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('address-search-wrapper')}
                >
                  <input type="text" placeholder="Search address..." />
                </div>
              </div>
              <button 
                className="expand-button"
                data-component="expand-button"
                onMouseEnter={(e) => handleComponentHover('expand-button', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('expand-button')}
              >
                <div className="expand-icon"></div>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Progress Tracking */}
      <section className="sandbox-section">
        <h2 className="section-title">Progress</h2>
        
        <div className="component-group">
          <h3 className="component-title">Progress Bar</h3>
          <div className="component-showcase">
            <div 
              className="apple-progress-tracker"
              data-component="apple-progress-tracker"
              onMouseEnter={(e) => handleComponentHover('apple-progress-tracker', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('apple-progress-tracker')}
            >
              <div 
                className="progress-container"
                data-component="progress-container"
                onMouseEnter={(e) => handleComponentHover('progress-container', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('progress-container')}
              >
                <div 
                  className="pill-progress-bar"
                  data-component="pill-progress-bar"
                  onMouseEnter={(e) => handleComponentHover('pill-progress-bar', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('pill-progress-bar')}
                >
                  <div className="pill-progress-fill" style={{ width: '75%' }}></div>
                </div>
                <p 
                  className="status-text"
                  data-component="status-text"
                  onMouseEnter={(e) => handleComponentHover('status-text', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('status-text')}
                >
                  Processing 3D model... 75% complete
                </p>
              </div>
              <div 
                className="action-buttons"
                data-component="action-buttons"
                onMouseEnter={(e) => handleComponentHover('action-buttons', e)}
                onMouseLeave={handleComponentLeave}
                onClick={() => handleComponentClick('action-buttons')}
              >
                <button 
                  className="stop-button"
                  data-component="stop-button"
                  onMouseEnter={(e) => handleComponentHover('stop-button', e)}
                  onMouseLeave={handleComponentLeave}
                  onClick={() => handleComponentClick('stop-button')}
                >
                  <span className="stop-icon">⏹</span>
                  Stop
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feedback */}
      <section className="sandbox-section">
        <h2 className="section-title">Feedback</h2>
        
        <div className="component-group">
          <h3 className="component-title">Status Messages</h3>
          <div className="component-showcase">
            <div 
              className="job-status"
              data-component="job-status"
              onMouseEnter={(e) => handleComponentHover('job-status', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('job-status')}
            >
              <h3>Processing Complete</h3>
              <p>Your 3D model has been successfully generated.</p>
            </div>
            <div 
              className="error-message"
              data-component="error-message"
              onMouseEnter={(e) => handleComponentHover('error-message', e)}
              onMouseLeave={handleComponentLeave}
              onClick={() => handleComponentClick('error-message')}
            >
              <h3>Processing Error</h3>
              <p>There was an issue processing your request.</p>
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
