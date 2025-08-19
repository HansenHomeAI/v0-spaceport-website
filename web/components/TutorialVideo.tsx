'use client';
import { useState } from 'react';

interface TutorialVideoProps {
  videoId: string;
  title?: string;
  description?: string;
}

export default function TutorialVideo({ 
  videoId, 
  title = "How to Use Spaceport - Tutorial", 
  description = "Watch this quick tutorial to learn how to create stunning 3D models with Spaceport" 
}: TutorialVideoProps): JSX.Element {
  const [isExpanded, setIsExpanded] = useState(false);

  const thumbnailUrl = `https://cdn.loom.com/sessions/thumbnails/${videoId}-with-play.gif`;
  const embedUrl = `https://www.loom.com/embed/${videoId}`;

  return (
    <div className="tutorial-video-container">
      {!isExpanded ? (
        <div className="tutorial-preview" onClick={() => setIsExpanded(true)}>
          <div className="tutorial-thumbnail">
            <img 
              src={thumbnailUrl} 
              alt={title}
              onError={(e) => {
                // Fallback to static thumbnail if GIF fails
                (e.target as HTMLImageElement).src = `https://cdn.loom.com/sessions/thumbnails/${videoId}.jpg`;
              }}
            />
            <div className="play-overlay">
              <div className="play-button">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M8 5v14l11-7z" fill="currentColor"/>
                </svg>
              </div>
            </div>
          </div>
          <div className="tutorial-info">
            <h3>{title}</h3>
            <p>{description}</p>
            <span className="watch-tutorial-cta">Click to watch tutorial →</span>
          </div>
        </div>
      ) : (
        <div className="tutorial-expanded">
          <div className="tutorial-header">
            <h3>{title}</h3>
            <button 
              className="collapse-button" 
              onClick={() => setIsExpanded(false)}
              aria-label="Close tutorial video"
            >
              ×
            </button>
          </div>
          <div className="tutorial-embed">
            <iframe
              src={embedUrl}
              frameBorder="0"
              allowFullScreen
              title={title}
            />
          </div>
        </div>
      )}
    </div>
  );
}
