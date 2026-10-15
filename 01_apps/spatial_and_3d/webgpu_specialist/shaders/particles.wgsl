// Lauburu Kinematic Particle Physics WGSL Compute Shader
// 64-thread workgroup execution for 120 FPS target render loop

struct Particle {
    position: vec4<f32>,
    velocity: vec4<f32>,
    color: vec4<f32>,
    torque: vec4<f32>,
};

struct ParticlesBuffer {
    particles: array<Particle>,
};

@group(0) @binding(0) var<storage, read_write> data: ParticlesBuffer;

struct SimParams {
    delta_time: f32,
    gravity: f32,
    damping: f32,
    node_count: u32,
};

@group(0) @binding(1) var<uniform> params: SimParams;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let index = global_id.x;
    if (index >= params.node_count || index >= arrayLength(&data.particles)) {
        return;
    }

    var p = data.particles[index];
    
    // Apply kinematic velocity & torque damping
    p.velocity.y -= params.gravity * params.delta_time;
    p.position += p.velocity * params.delta_time;
    p.velocity *= params.damping;

    // Tatami bounds collision (3D bounding cube [-5.0, 5.0])
    if (p.position.x < -5.0 || p.position.x > 5.0) {
        p.velocity.x = -p.velocity.x * 0.8;
        p.position.x = clamp(p.position.x, -5.0, 5.0);
    }
    if (p.position.y < 0.0) {
        p.velocity.y = -p.velocity.y * 0.7; // Mat bounce
        p.position.y = 0.0;
    }
    if (p.position.z < -5.0 || p.position.z > 5.0) {
        p.velocity.z = -p.velocity.z * 0.8;
        p.position.z = clamp(p.position.z, -5.0, 5.0);
    }

    data.particles[index] = p;
}
