// src/hooks/useOffline.js
// Simple network status monitoring

import { useState, useEffect } from 'react';

export function useOffline() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [connectionType, setConnectionType] = useState('unknown');

  useEffect(() => {
    const updateOnlineStatus = () => {
      setIsOnline(navigator.onLine);
    };

    const updateConnectionType = () => {
      // Get connection info if available
      const connection = navigator.connection 
        || navigator.mozConnection 
        || navigator.webkitConnection;
      
      if (connection) {
        setConnectionType(connection.effectiveType || connection.type || 'unknown');
      }
    };

    // Set initial connection type
    updateConnectionType();

    // Event listeners
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);

    // Connection change listener (if supported)
    const connection = navigator.connection 
      || navigator.mozConnection 
      || navigator.webkitConnection;
    
    if (connection) {
      connection.addEventListener('change', updateConnectionType);
    }

    // Cleanup
    return () => {
      window.removeEventListener('online', updateOnlineStatus);
      window.removeEventListener('offline', updateOnlineStatus);
      
      if (connection) {
        connection.removeEventListener('change', updateConnectionType);
      }
    };
  }, []);

  return {
    isOnline,
    connectionType,
    isOffline: !isOnline
  };
}