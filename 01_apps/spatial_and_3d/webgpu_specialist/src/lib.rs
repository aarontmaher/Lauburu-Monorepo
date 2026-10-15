//! Lauburu WebGPU & Rust 3D Spatial Grappling Kinematics Bridge
//! Bridges high-performance Rust wgpu compute and WGSL shaders with WebAssembly.

use bytemuck::{Pod, Zeroable};
use glam::{Mat4, Vec3};
use wasm_bindgen::prelude::*;

#[repr(C)]
#[derive(Copy, Clone, Debug, Pod, Zeroable)]
pub struct Particle {
    pub position: [f32; 4],
    pub velocity: [f32; 4],
    pub color: [f32; 4],
    pub torque: [f32; 4],
}

#[repr(C)]
#[derive(Copy, Clone, Debug, Pod, Zeroable)]
pub struct SimParams {
    pub delta_time: f32,
    pub gravity: f32,
    pub damping: f32,
    pub node_count: u32,
}

#[repr(C)]
#[derive(Copy, Clone, Debug, Pod, Zeroable)]
pub struct CameraUniform {
    pub view_proj: [[f32; 4]; 4],
    pub camera_pos: [f32; 4],
}

#[repr(C)]
#[derive(Copy, Clone, Debug, Pod, Zeroable)]
pub struct Vertex {
    pub position: [f32; 3],
    pub color: [f32; 4],
    pub normal: [f32; 3],
}

#[wasm_bindgen]
pub struct SpatialKinematicsEngine {
    node_count: u32,
    fps_estimate: f32,
}

#[wasm_bindgen]
impl SpatialKinematicsEngine {
    #[wasm_bindgen(constructor)]
    pub fn new(node_count: u32) -> Self {
        console_error_panic_hook::set_once();
        Self {
            node_count,
            fps_estimate: 120.0,
        }
    }

    #[wasm_bindgen]
    pub fn get_node_count(&self) -> u32 {
        self.node_count
    }

    #[wasm_bindgen]
    pub fn get_fps_target(&self) -> f32 {
        self.fps_estimate
    }

    #[wasm_bindgen]
    pub fn compute_joint_torques(&self, angle_rad: f32, angular_velocity: f32) -> f32 {
        // Biomechanical joint torque model for Grappling Kinematics
        let moment_arm = 0.35; // meters
        let muscle_force = 450.0 * (1.0 - (angle_rad - 1.57).abs() / 1.57);
        let dynamic_torque = muscle_force * moment_arm - 12.5 * angular_velocity;
        dynamic_torque.max(0.0)
    }

    #[wasm_bindgen]
    pub fn generate_camera_matrix(&self, eye_x: f32, eye_y: f32, eye_z: f32, aspect: f32) -> Vec<f32> {
        let eye = Vec3::new(eye_x, eye_y, eye_z);
        let center = Vec3::ZERO;
        let up = Vec3::Y;
        let view = Mat4::look_at_rh(eye, center, up);
        let proj = Mat4::perspective_rh(45.0_f32.to_radians(), aspect, 0.1, 100.0);
        let view_proj = proj * view;
        
        let mut out = Vec::with_capacity(16);
        for col in view_proj.to_cols_array_2d() {
            out.extend_from_slice(&col);
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_initialization() {
        let engine = SpatialKinematicsEngine::new(955);
        assert_eq!(engine.get_node_count(), 955);
        assert_eq!(engine.get_fps_target(), 120.0);
    }

    #[test]
    fn test_joint_torque_calculation() {
        let engine = SpatialKinematicsEngine::new(955);
        let torque = engine.compute_joint_torques(1.57, 0.0);
        assert!(torque > 150.0);
    }

    #[test]
    fn test_camera_matrix_generation() {
        let engine = SpatialKinematicsEngine::new(955);
        let matrix = engine.generate_camera_matrix(0.0, 5.0, 10.0, 16.0 / 9.0);
        assert_eq!(matrix.len(), 16);
    }
}
