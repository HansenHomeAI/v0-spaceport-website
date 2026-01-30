'use client';

import React, { useState, useRef, useEffect } from 'react';

type FAQItem = {
  question: string;
  answer: string;
};

const FAQ_ITEMS: FAQItem[] = [
  {
    question: "How long does processing take?",
    answer: "Most models are ready within 24 hours. Larger properties may take slightly longer, but we always prioritize speed without compromising quality."
  },
  {
    question: "Do I need a specific drone?",
    answer: "We support most DJI drones including Mini, Air, and Mavic series. If you have a different drone, contact us to check compatibility."
  },
  {
    question: "Can I embed models on my website?",
    answer: "Yes! We provide a simple link and embed code compatible with all major website builders and MLS platforms."
  },
  {
    question: "How much does it cost?",
    answer: "We offer competitive pricing per property. Join our waitlist to see our full pricing tier and early-access offers."
  }
];

export default function FAQ(): JSX.Element {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggleItem = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section className="section two-col-section" id="faq" style={{ padding: '70px 0 40px' }}>
      <div className="two-col-content" style={{ 
        maxWidth: '900px', 
        margin: '0 auto', 
        textAlign: 'left'
      }}>
        <h2 style={{ 
          textAlign: 'left', 
          marginBottom: '2rem', 
          fontSize: '2rem', 
          fontWeight: 500, // Matched with .section h2
          color: 'white'
        }}>
          Frequently Asked Questions
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

function FAQItem({ item, isOpen, onClick }: { item: FAQItem, isOpen: boolean, onClick: () => void }) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (isOpen && contentRef.current) {
      setHeight(contentRef.current.scrollHeight);
    } else {
      setHeight(0);
    }
  }, [isOpen]);

  return (
    <div style={{ 
      borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
      marginBottom: '10px'
    }}>
      <button 
        onClick={onClick}
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
          outline: 'none'
        }}
        aria-expanded={isOpen}
      >
        <span style={{ opacity: 1 }}>{item.question}</span>
        <div style={{ 
          transform: isOpen ? 'rotate(-90deg)' : 'rotate(90deg)',
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
            color: 'rgba(255, 255, 255, 0.5)',
            lineHeight: '1.6',
            fontSize: '1.1rem',
            textAlign: 'left'
          }}
        >
          {item.answer}
        </div>
      </div>
    </div>
  );
}
