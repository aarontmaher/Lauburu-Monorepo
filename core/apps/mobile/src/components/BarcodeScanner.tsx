/**
 * Barcode scanner modal — uses expo-camera CameraView with barcode
 * scanning. Opens as a full-screen overlay, scans continuously,
 * and calls onScanned with the first valid barcode detected.
 *
 * Falls back gracefully in Expo Go (no native camera module) by
 * showing a message to use the text input instead.
 */
import React, { useState, useCallback, useRef } from 'react';
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  Modal,
  Platform,
} from 'react-native';

let CameraView: any = null;
let useCameraPermissions: any = null;
try {
  const mod = require('expo-camera');
  CameraView = mod.CameraView;
  useCameraPermissions = mod.useCameraPermissions;
} catch {
  // expo-camera not available (e.g. Expo Go without dev client).
}

interface BarcodeScannerProps {
  visible: boolean;
  onScanned: (barcode: string) => void;
  onClose: () => void;
}

export function BarcodeScanner({ visible, onScanned, onClose }: BarcodeScannerProps) {
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const scannedRef = useRef(false);

  // Request permission when the modal opens.
  const requestPermission = useCallback(async () => {
    if (!CameraView) return;
    try {
      const mod = require('expo-camera');
      const result = await mod.Camera?.requestCameraPermissionsAsync?.()
        ?? await mod.requestCameraPermissionsAsync?.();
      setHasPermission(result?.granted ?? false);
    } catch {
      setHasPermission(false);
    }
  }, []);

  const handleBarcodeScanned = useCallback(
    (event: { data: string; type: string }) => {
      if (scannedRef.current) return;
      const barcode = event.data?.trim();
      if (!barcode || !/^\d{6,14}$/.test(barcode)) return;
      scannedRef.current = true;
      onScanned(barcode);
    },
    [onScanned],
  );

  const handleShow = useCallback(() => {
    scannedRef.current = false;
    requestPermission();
  }, [requestPermission]);

  if (!CameraView) {
    return (
      <Modal visible={visible} animationType="slide" onShow={handleShow}>
        <View style={styles.fallbackContainer}>
          <Text style={styles.fallbackText}>
            Camera not available in this build.{'\n'}
            Use the text input to enter the barcode manually.
          </Text>
          <Pressable style={styles.closeBtn} onPress={onClose}>
            <Text style={styles.closeBtnText}>Close</Text>
          </Pressable>
        </View>
      </Modal>
    );
  }

  return (
    <Modal
      visible={visible}
      animationType="slide"
      onShow={handleShow}
      presentationStyle="fullScreen">
      <View style={styles.container}>
        {hasPermission === false && (
          <View style={styles.fallbackContainer}>
            <Text style={styles.fallbackText}>
              Camera permission denied.{'\n'}
              Grant camera access in Settings to scan barcodes.
            </Text>
            <Pressable style={styles.closeBtn} onPress={onClose}>
              <Text style={styles.closeBtnText}>Close</Text>
            </Pressable>
          </View>
        )}
        {hasPermission === true && (
          <>
            <CameraView
              style={StyleSheet.absoluteFill}
              facing="back"
              barcodeScannerSettings={{
                barcodeTypes: ['ean13', 'ean8', 'upc_a', 'upc_e', 'code128', 'code39'],
              }}
              onBarcodeScanned={handleBarcodeScanned}
            />
            {/* Scanning overlay */}
            <View style={styles.overlay}>
              <View style={styles.overlayTop} />
              <View style={styles.overlayMiddle}>
                <View style={styles.overlaySide} />
                <View style={styles.scanWindow}>
                  <View style={[styles.corner, styles.cornerTL]} />
                  <View style={[styles.corner, styles.cornerTR]} />
                  <View style={[styles.corner, styles.cornerBL]} />
                  <View style={[styles.corner, styles.cornerBR]} />
                </View>
                <View style={styles.overlaySide} />
              </View>
              <View style={styles.overlayBottom}>
                <Text style={styles.scanHint}>
                  Point at a barcode on the package
                </Text>
                <Pressable style={styles.closeBtn} onPress={onClose}>
                  <Text style={styles.closeBtnText}>Cancel</Text>
                </Pressable>
              </View>
            </View>
          </>
        )}
        {hasPermission === null && (
          <View style={styles.fallbackContainer}>
            <Text style={styles.fallbackText}>Requesting camera access…</Text>
          </View>
        )}
      </View>
    </Modal>
  );
}

const SCAN_SIZE = 250;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  fallbackContainer: {
    flex: 1,
    backgroundColor: '#111',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  fallbackText: {
    color: '#aaa',
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 24,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
  },
  overlayTop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
  },
  overlayMiddle: {
    flexDirection: 'row',
    height: SCAN_SIZE,
  },
  overlaySide: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
  },
  scanWindow: {
    width: SCAN_SIZE,
    height: SCAN_SIZE,
  },
  overlayBottom: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    alignItems: 'center',
    paddingTop: 24,
  },
  scanHint: {
    color: '#fff',
    fontSize: 15,
    marginBottom: 20,
  },
  corner: {
    position: 'absolute',
    width: 24,
    height: 24,
    borderColor: '#d4e157',
    borderWidth: 3,
  },
  cornerTL: { top: 0, left: 0, borderRightWidth: 0, borderBottomWidth: 0 },
  cornerTR: { top: 0, right: 0, borderLeftWidth: 0, borderBottomWidth: 0 },
  cornerBL: { bottom: 0, left: 0, borderRightWidth: 0, borderTopWidth: 0 },
  cornerBR: { bottom: 0, right: 0, borderLeftWidth: 0, borderTopWidth: 0 },
  closeBtn: {
    backgroundColor: '#333',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  closeBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
