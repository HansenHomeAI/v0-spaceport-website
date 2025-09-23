'use client';

import React, { useState } from 'react';
import ModelDeliveryModal from './ModelDeliveryModal';
import { useModelDelivery } from '../app/hooks/useModelDelivery';

export default function ModelDeliveryManager(): JSX.Element | null {
  const modelDelivery = useModelDelivery();
  const [modalOpen, setModalOpen] = useState(false);

  if (modelDelivery.loading) {
    return null;
  }

  if (!modelDelivery.hasPermission) {
    return null;
  }

  const openModal = () => {
    modelDelivery.clearError();
    setModalOpen(true);
  };

  const closeModal = () => {
    modelDelivery.clearError();
    setModalOpen(false);
  };

  return (
    <>
      <div className="model-delivery-card">
        <div className="card-header">
          <div>
            <h4>Model Delivery</h4>
            <p>Share finished ML outputs directly with clients from inside the dashboard.</p>
          </div>
          <button className="card-button" onClick={openModal}>
            Deliver Model
          </button>
        </div>
        <ul className="card-list">
          <li>Look up any client by email and confirm their project.</li>
          <li>Paste the hosted link from Spaceport storage or ML pipeline.</li>
          <li>We update the project modal and send an email via Resend instantly.</li>
        </ul>
      </div>

      {modalOpen && (
        <ModelDeliveryModal
          open={modalOpen}
          onClose={closeModal}
          projects={modelDelivery.projects}
          fetchingProjects={modelDelivery.fetchingProjects}
          sendingDelivery={modelDelivery.sendingDelivery}
          fetchProjects={modelDelivery.fetchProjects}
          sendDelivery={modelDelivery.sendDelivery}
          clearError={modelDelivery.clearError}
          error={modelDelivery.error}
        />
      )}

      <style jsx>{`
        .model-delivery-card {
          margin-top: 24px;
          padding: 24px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          backdrop-filter: blur(10px);
          color: #ffffff;
        }
        .card-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 20px;
        }
        .card-header h4 {
          margin: 0;
          font-size: 1.125rem;
          font-weight: 600;
        }
        .card-header p {
          margin: 6px 0 0 0;
          color: rgba(255, 255, 255, 0.68);
          font-size: 0.9rem;
        }
        .card-button {
          border: none;
          border-radius: 50px;
          padding: 12px 28px;
          background: #ffffff;
          color: #05070f;
          font-weight: 600;
          cursor: pointer;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
          white-space: nowrap;
        }
        .card-button:hover {
          transform: translateY(-1px);
          box-shadow: 0 10px 28px rgba(255, 255, 255, 0.25);
        }
        .card-list {
          margin: 18px 0 0 18px;
          padding: 0;
          color: rgba(255, 255, 255, 0.6);
          font-size: 0.9rem;
        }
        .card-list li {
          margin-bottom: 10px;
        }
        @media (max-width: 768px) {
          .card-header {
            flex-direction: column;
            align-items: flex-start;
          }
          .card-button {
            width: 100%;
          }
        }
      `}</style>
    </>
  );
}
