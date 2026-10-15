package com.lauburu.ble;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothProfile;
import android.content.Context;
import android.os.Looper;

import java.io.OutputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.UUID;

public class BleBridge {
    private static final String TAG = "LauburuBleBridge";
    
    private static final UUID MOVESENSE_SERVICE = UUID.fromString("34802252-7185-4d5d-b431-630e7050e8f0");
    private static final UUID MOVESENSE_COMMAND = UUID.fromString("34800001-7185-4d5d-b431-630e7050e8f0");
    private static final UUID MOVESENSE_DATA = UUID.fromString("34800002-7185-4d5d-b431-630e7050e8f0");
    private static final UUID CLIENT_CHARACTERISTIC_CONFIG = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: app_process /system/bin com.lauburu.ble.BleBridge <MAC_ADDRESS>");
            System.exit(1);
        }
        String macAddress = args[0];
        System.out.println("Starting Lauburu Shizuku BLE Bridge for: " + macAddress);

        try {
            Looper.prepare();
            Context tempContext = (Context) Class.forName("android.app.ActivityThread")
                    .getMethod("currentApplication")
                    .invoke(null);

            if (tempContext == null) {
                tempContext = (Context) Class.forName("android.app.ActivityThread")
                        .getMethod("systemMain")
                        .invoke(null)
                        .getClass()
                        .getMethod("getSystemContext")
                        .invoke(Class.forName("android.app.ActivityThread").getMethod("systemMain").invoke(null));
            }
            final Context context = tempContext;

            BluetoothManager bluetoothManager = (BluetoothManager) context.getSystemService(Context.BLUETOOTH_SERVICE);
            BluetoothAdapter bluetoothAdapter = bluetoothManager.getAdapter();

            final BluetoothDevice device = bluetoothAdapter.getRemoteDevice(macAddress);
            System.out.println("Device found. Attempting GATT connect...");

            final ServerSocket serverSocket = new ServerSocket(19003);
            System.out.println("Listening for AVF connection on TCP 19003...");
            
            new Thread(new Runnable() {
                @Override
                public void run() {
                    try {
                        Socket clientSocket = serverSocket.accept();
                        System.out.println("AVF Client Connected!");
                        final OutputStream out = clientSocket.getOutputStream();
                        
                        BluetoothGattCallback gattCallback = new BluetoothGattCallback() {
                            @Override
                            public void onConnectionStateChange(BluetoothGatt gatt, int status, int newState) {
                                if (newState == BluetoothProfile.STATE_CONNECTED) {
                                    System.out.println("GATT Connected! Discovering services...");
                                    gatt.discoverServices();
                                }
                            }

                            @Override
                            public void onServicesDiscovered(BluetoothGatt gatt, int status) {
                                if (status == BluetoothGatt.GATT_SUCCESS) {
                                    System.out.println("Services discovered. Enabling ECG 512Hz stream...");
                                    BluetoothGattCharacteristic dataChar = gatt.getService(MOVESENSE_SERVICE).getCharacteristic(MOVESENSE_DATA);
                                    gatt.setCharacteristicNotification(dataChar, true);
                                    BluetoothGattDescriptor desc = dataChar.getDescriptor(CLIENT_CHARACTERISTIC_CONFIG);
                                    desc.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
                                    gatt.writeDescriptor(desc);

                                    BluetoothGattCharacteristic cmdChar = gatt.getService(MOVESENSE_SERVICE).getCharacteristic(MOVESENSE_COMMAND);
                                    byte[] startCommand = new byte[]{1, 99, 2, 1, 0};
                                    cmdChar.setValue(startCommand);
                                    gatt.writeCharacteristic(cmdChar);
                                }
                            }

                            @Override
                            public void onCharacteristicChanged(BluetoothGatt gatt, BluetoothGattCharacteristic characteristic) {
                                if (MOVESENSE_DATA.equals(characteristic.getUuid())) {
                                    try {
                                        out.write(characteristic.getValue());
                                        out.flush();
                                    } catch (Exception e) {
                                        e.printStackTrace();
                                    }
                                }
                            }
                        };

                        device.connectGatt(context, false, gattCallback);

                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            }).start();

            Looper.loop();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
