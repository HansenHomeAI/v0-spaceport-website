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
    <section className="section" id="faq" style={{ padding: '70px 20px 40px' }}>
      <div style={{ maxWidth: '900px', margin: '0 auto', textAlign: 'left' }}>
        <h2 style={{ 
          textAlign: 'left', 
          marginBottom: '2rem', 
          fontSize: '2rem', 
          fontWeight: 500, // Matched with .section h2
          color: 'white'
        }}>
          Frequently Asked Questions
        </h2>
        
        <div className="faq-list" style={{ maxWidth: '800px' }}>
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
          fontSize: '1.2rem', // Matched with .section p
          fontWeight: 400, // Matched with .section p
          outline: 'none'
        }}
        aria-expanded={isOpen}
      >
        <span style={{ opacity: isOpen ? 1 : 0.8, transition: 'opacity 0.3s' }}>{item.question}</span>
        <div style={{ 
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.3s ease',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '24px',
          height: '24px',
          opacity: 0.5, // Set to 50% opacity
          color: 'white'
        }}>
          <svg width="14" height="9" viewBox="0 0 14 9" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M1 1L7 7L13 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
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
            color: 'rgba(255, 255, 255, 0.5)', // White at 50% opacity
            lineHeight: '1.6',
            fontSize: '1.1rem',
            textAlign: 'left' // Ensure left alignment
          }}
        >
          {item.answer}
        </div>
      </div>
    </div>
  );
}
