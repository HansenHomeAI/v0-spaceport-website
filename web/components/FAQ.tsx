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
    <section className="section" id="faq" style={{ padding: '4rem 0' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '0 20px' }}>
        <h2 style={{ 
          textAlign: 'left', 
          marginBottom: '2rem', 
          fontSize: '2rem', 
          fontWeight: 600,
          color: 'white' // Assuming dark theme based on other components
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
      borderBottom: '1px solid rgba(255, 255, 255, 0.1)', // Thin rounded line look
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
          fontSize: '1.1rem',
          fontWeight: 500,
          outline: 'none'
        }}
        aria-expanded={isOpen}
      >
        <span>{item.question}</span>
        <div style={{ 
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.3s ease',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '24px',
          height: '24px',
          opacity: 0.7
        }}>
          <svg width="14" height="9" viewBox="0 0 14 9" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M1 1L7 7L13 1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </button>
      
      <div 
        style={{ 
          height: `${height}px`, 
          overflow: 'hidden', 
          transition: 'height 0.3s ease-in-out',
          opacity: isOpen ? 1 : 0.5
        }}
      >
        <div ref={contentRef} style={{ paddingBottom: '24px', color: 'rgba(255, 255, 255, 0.8)', lineHeight: '1.6' }}>
          {item.answer}
        </div>
      </div>
    </div>
  );
}
