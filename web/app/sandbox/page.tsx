'use client';

import React from 'react';
import './sandbox.css';

export default function DesignSystemSandbox(): JSX.Element {
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
          <h3 className="component-title">Headings</h3>
          <div className="component-showcase">
            <h1 className="section h1">Heading 1</h1>
            <h2 className="section h2">Heading 2</h2>
            <h3 className="component-title">Heading 3</h3>
            <h4 className="popup-section h4">Heading 4</h4>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Body Text</h3>
          <div className="component-showcase">
            <p className="section p">Primary paragraph text</p>
            <p className="waitlist-header p">Secondary text</p>
            <p className="stats-source">Tertiary text</p>
          </div>
        </div>
      </section>

      {/* Buttons */}
      <section className="sandbox-section">
        <h2 className="section-title">Buttons</h2>
        
        <div className="component-group">
          <h3 className="component-title">Primary Actions</h3>
          <div className="component-showcase">
            <a href="#" className="cta-button">Primary CTA</a>
            <a href="#" className="cta-button2-fixed">Secondary CTA</a>
            <button className="dpu-btn">Submit</button>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Secondary Actions</h3>
          <div className="component-showcase">
            <button className="stop-button">Stop</button>
            <button className="add-path-button">Add Path</button>
            <button className="info-pill-icon">Info</button>
          </div>
        </div>
      </section>

      {/* Form Elements */}
      <section className="sandbox-section">
        <h2 className="section-title">Form Elements</h2>
        
        <div className="component-group">
          <h3 className="component-title">Inputs</h3>
          <div className="component-showcase">
            <div className="input-wrapper">
              <input type="text" placeholder="Standard input" />
            </div>
            <div className="popup-input-wrapper">
              <img src="/assets/SpaceportIcons/Pin.svg" className="input-icon pin" alt="" />
              <input type="text" placeholder="Input with icon" />
            </div>
            <div className="popup-input-wrapper has-suffix" data-suffix="acres">
              <img src="/assets/SpaceportIcons/Number.svg" className="input-icon number" alt="" />
              <input type="number" placeholder="Input with suffix" />
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Textarea</h3>
          <div className="component-showcase">
            <div className="popup-input-wrapper listing-description-wrapper">
              <img src="/assets/SpaceportIcons/Paragraph.svg" className="input-icon paragraph" alt="" />
              <textarea placeholder="Multi-line input"></textarea>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Select</h3>
          <div className="component-showcase">
            <label className="step-selector-label">Pipeline Step</label>
            <select className="step-selector">
              <option value="sfm">SfM Processing</option>
              <option value="3dgs">3D Gaussian Splatting</option>
              <option value="compression">Compression</option>
            </select>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Toggle</h3>
          <div className="component-showcase">
            <div className="ios-toggle-container">
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
          <h3 className="component-title">Project Cards</h3>
          <div className="component-showcase">
            <div className="project-box">
              <h1>Sample Project</h1>
              <p>Project description</p>
            </div>
            <div className="new-project-card">
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
            <div className="waitlist-card">
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
            <div className="upload-zone">
              <div className="upload-icon"></div>
              <p>Drag & drop files here</p>
              <p className="upload-hint">or click to browse</p>
            </div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Progress</h3>
          <div className="component-showcase">
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: '65%' }}></div>
            </div>
            <div className="spinner"></div>
          </div>
        </div>

        <div className="component-group">
          <h3 className="component-title">Status</h3>
          <div className="component-showcase">
            <div className="status-indicator">
              <div className="status-dot pending"></div>
              <span>Pending</span>
            </div>
            <div className="status-indicator">
              <div className="status-dot processing"></div>
              <span>Processing</span>
            </div>
            <div className="status-indicator">
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
            <div className="popup-overlay" style={{ position: 'relative', height: '300px' }}>
              <div className="popup-content-scroll">
                <div className="popup-header">
                  <div className="popup-title-section">
                    <input className="popup-title-input" placeholder="Project Title" />
                  </div>
                  <button className="popup-close"></button>
                </div>
                <div className="accordion-section active">
                  <div className="accordion-header">
                    <div className="accordion-title">
                      <h3>Property Details</h3>
                    </div>
                    <div className="accordion-chevron"></div>
                  </div>
                  <div className="accordion-content">
                    <p className="section-description">Enter the basic details about your property.</p>
                    <div className="category-outline">
                      <h4>Basic Information</h4>
                      <div className="popup-section">
                        <div className="input-row-popup">
                          <div className="popup-input-wrapper">
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
            <div className="map-wrapper">
              <div className="map-container">
                <div className="map-blur-background"></div>
                <div className="map-instructions-center">
                  <div className="instruction-content">
                    <div className="instruction-pin"></div>
                    <h3>Click to place property marker</h3>
                  </div>
                </div>
              </div>
              <div className="address-search-overlay">
                <div className="address-search-wrapper">
                  <input type="text" placeholder="Search address..." />
                </div>
              </div>
              <button className="expand-button">
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
            <div className="apple-progress-tracker">
              <div className="progress-container">
                <div className="pill-progress-bar">
                  <div className="pill-progress-fill" style={{ width: '75%' }}></div>
                </div>
                <p className="status-text">Processing 3D model... 75% complete</p>
              </div>
              <div className="action-buttons">
                <button className="stop-button">
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
            <div className="job-status">
              <h3>Processing Complete</h3>
              <p>Your 3D model has been successfully generated.</p>
            </div>
            <div className="error-message">
              <h3>Processing Error</h3>
              <p>There was an issue processing your request.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
