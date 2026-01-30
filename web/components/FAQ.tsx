'use client';

import React, { useState, useRef, useEffect } from 'react';

type FAQItem = {
  question: string;
  answer: string;
};

/** Section headers in answers that should be 100% white for emphasis/hierarchy */
const FAQ_EMPHASIS_HEADERS = [
  "Supported by the standard Litchi app (Litchi for DJI Drones):",
  "Supported by Litchi Pilot:",
  "Not supported by either Litchi app (no Litchi/Litchi Pilot flight control):",
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: "Who captures the photos?",
    answer: "We provide the software to make it extremely easy for you or your drone pilot to create a 3D space—no skill required."
  },
  {
    question: "What drones are supported?",
    answer: "We use Litchi as the flight controller to run the generated flight paths.\n\nSupported by the standard Litchi app (Litchi for DJI Drones): Mini 2, Mini SE (version 1 only), Air 2S, Mavic Mini 1, Mavic Air 2, Mavic 2 (Zoom/Pro), Mavic (Air/Pro), Phantom 4 (Standard/Advanced/Pro/ProV2), Phantom 3 (Standard/4K/Advanced/Professional), Inspire 1 (X3/Z3/Pro/RAW), Inspire 2, Spark.\n\nSupported by Litchi Pilot: Mini 4 Pro, Mini 3, Mini 3 Pro, Matrice 4 (4E/4T/4D/4TD), Mavic 3 Enterprise (3E/3T/3M), Matrice 30, Matrice 300 RTK, Matrice 350 RTK, Matrice 400.\n\nNot supported by either Litchi app (no Litchi/Litchi Pilot flight control): Mini 5 Pro, Air 3, Air 3S, Mavic 3, Mavic 3 Classic, Mavic 3 Pro, Mavic 4 Pro, Mini 2 SE, Mini 4K, Inspire 3, Avata, Avata 2, DJI FPV, DJI Flip, DJI Neo, DJI Neo 2, DJI O3 Air Unit, DJI O4 Air Unit Series."
  },
  {
    question: "What are the steps to capture?",
    answer: "This software generates the flight paths, automatically sends them to your drone controller app, and once you upload the photos after the flight, trains a 3D model on them.\n\nThe DJI remote must use a phone (not an embedded screen) to run the third-party Litchi drone controller app. This app is the most widely used, reliable standard for complicated autonomous missions. You simply press 'Go' on each of the flight paths in Litchi, swapping batteries between each completed path. The drone flies itself—no skill required.\n\nWhen uploading the completed drone photos, do not edit coloring or remove any metadata beforehand. The naming and ordering of the photos do not impact the result.\n\nWhen you create an account, you'll have access to a tutorial that guides you through these steps in more detail."
  },
  {
    question: "How long does processing take?",
    answer: "It takes up to 3 days to fully train your 3D space (a custom AI model). We are actively working to get that time down to 3 hours or less."
  }
];

export default function FAQ(): JSX.Element {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggleItem = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section className="section" id="faq" style={{ padding: '70px 20px 40px' }}>
      <div className="faq-content">
        <h2 style={{ 
          textAlign: 'left', 
          marginBottom: '2rem', 
          fontSize: '2rem', 
          fontWeight: 500, // Matched with .section h2
          color: 'white'
        }}>
          Common questions.
        </h2>
        
        <div className="faq-list">
          {FAQ_ITEMS.map((item, index) => (
            <FAQItem 
              key={index} 
              item={item} 
              isOpen={openIndex === index} 
              onClick={() => toggleItem(index)} 
            />
          ))}
        </div>
      </div>
    </section>
  );
}

const answerBaseStyle: React.CSSProperties = {
  color: 'rgba(255, 255, 255, 0.5)',
  lineHeight: 1.6,
  fontSize: '1.1rem',
  textAlign: 'left',
};

function renderAnswerWithEmphasis(answer: string): React.ReactNode {
  const hasEmphasis = FAQ_EMPHASIS_HEADERS.some((h) => answer.includes(h));
  if (!hasEmphasis) {
    return answer;
  }
  const paragraphs = answer.split('\n\n');
  return paragraphs.map((para, i) => {
    let header: string | null = null;
    let rest = para;
    for (const prefix of FAQ_EMPHASIS_HEADERS) {
      if (para.startsWith(prefix)) {
        header = prefix;
        rest = para.slice(prefix.length).trimStart();
        break;
      }
    }
    const marginBottom = i < paragraphs.length - 1 ? '1rem' : 0;
    if (header) {
      return (
        <div key={i} style={{ ...answerBaseStyle, marginBottom }}>
          <span style={{ color: 'white' }}>{header}</span>
          {rest ? ` ${rest}` : null}
        </div>
      );
    }
    return (
      <div key={i} style={{ ...answerBaseStyle, marginBottom }}>
        {para}
      </div>
    );
  });
}

function FAQItem({ item, isOpen, onClick }: { item: FAQItem, isOpen: boolean, onClick: () => void }) {
  const contentRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [height, setHeight] = useState(0);
  const hasEmphasis = FAQ_EMPHASIS_HEADERS.some((h) => item.answer.includes(h));

  useEffect(() => {
    if (isOpen && contentRef.current) {
      setHeight(contentRef.current.scrollHeight);
    } else {
      setHeight(0);
    }
  }, [isOpen]);

  const handleClick = () => {
    const button = buttonRef.current;
    if (!button) {
      onClick();
      return;
    }

    // Capture current position relative to viewport before state change
    const startTop = button.getBoundingClientRect().top;
    
    onClick();

    // Continuously correct scroll position during the transition to "stick" the element
    // This prevents disorientation when content above collapses
    const startTime = performance.now();
    const duration = 350; // Match transition time + buffer

    const loop = (now: number) => {
      if (now - startTime > duration) return;

      const currentTop = button.getBoundingClientRect().top;
      const diff = currentTop - startTop;

      // If element moved, instantly correct scroll to keep it in place
      if (Math.abs(diff) > 1) {
        window.scrollBy({ top: diff, behavior: 'instant' as ScrollBehavior });
      }

      requestAnimationFrame(loop);
    };

    requestAnimationFrame(loop);
  };

  return (
    <div style={{ 
      borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
      marginBottom: '10px'
    }}>
      <button 
        ref={buttonRef}
        onClick={handleClick}
        style={{
          width: '100%',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '20px 0',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
          color: 'white',
          fontSize: '1.2rem',
          fontWeight: 400,
          outline: 'none',
          scrollMarginTop: '100px' // Ensure it doesn't snap to the very top edge
        }}
        aria-expanded={isOpen}
      >
        <span style={{ opacity: 1 }}>{item.question}</span>
        <div style={{ 
          transform: isOpen ? 'rotate(270deg)' : 'rotate(90deg)',
          transition: 'transform 0.3s ease',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '24px',
          height: '24px',
          opacity: 0.5
        }}>
          <img 
            src="/assets/SpaceportIcons/Arrow.svg" 
            alt="" 
            style={{ width: '12px', height: '12px', filter: 'brightness(0) invert(1)' }} 
          />
        </div>
      </button>
      
      <div 
        style={{ 
          height: `${height}px`, 
          overflow: 'hidden', 
          transition: 'height 0.3s ease-in-out',
        }}
      >
        <div 
          ref={contentRef} 
          style={{ 
            paddingBottom: '24px', 
            ...answerBaseStyle,
            whiteSpace: hasEmphasis ? 'normal' : 'pre-line'
          }}
        >
          {hasEmphasis ? renderAnswerWithEmphasis(item.answer) : item.answer}
        </div>
      </div>
    </div>
  );
}
