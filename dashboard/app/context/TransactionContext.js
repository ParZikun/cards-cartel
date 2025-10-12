'use client'

import React, { createContext, useState, useContext } from 'react';

const TransactionContext = createContext();

export function useTransaction() {
  return useContext(TransactionContext);
}

export function TransactionProvider({ children }) {
  const [priorityFee, setPriorityFee] = useState(0); // Default to 0 microlamports
  const [slippage, setSlippage] = useState(0.5); // Default to 0.5%

  const value = {
    priorityFee,
    setPriorityFee,
    slippage,
    setSlippage,
  };

  return (
    <TransactionContext.Provider value={value}>
      {children}
    </TransactionContext.Provider>
  );
}
