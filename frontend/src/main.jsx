import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import './styles.css';
const rootEl = document.getElementById('root');
createRoot(rootEl).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>
);
