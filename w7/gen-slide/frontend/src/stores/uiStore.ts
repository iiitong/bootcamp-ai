// stores/uiStore.ts

import { create } from 'zustand';

interface UIState {
  isStyleModalOpen: boolean;
  isFullscreenPlaying: boolean;
  playStartSid: string | null;

  // Actions
  openStyleModal: () => void;
  closeStyleModal: () => void;
  startPlayback: (startSid: string) => void;
  stopPlayback: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  isStyleModalOpen: false,
  isFullscreenPlaying: false,
  playStartSid: null,

  openStyleModal: () => {
    set({ isStyleModalOpen: true });
  },

  closeStyleModal: () => {
    set({ isStyleModalOpen: false });
  },

  startPlayback: (startSid: string) => {
    set({
      isFullscreenPlaying: true,
      playStartSid: startSid,
    });
  },

  stopPlayback: () => {
    set({
      isFullscreenPlaying: false,
      playStartSid: null,
    });
  },
}));
