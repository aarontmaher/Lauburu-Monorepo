import { create } from 'zustand';

interface MapUiState {
  /** True while a node detail panel is visible inside the Map WebView. */
  nodeDetailOpen: boolean;
  setNodeDetailOpen: (open: boolean) => void;
}

export const useMapUiStore = create<MapUiState>((set) => ({
  nodeDetailOpen: false,
  setNodeDetailOpen: (open) => set({ nodeDetailOpen: open }),
}));
