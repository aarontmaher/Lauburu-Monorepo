// Lauburu 3D Spatial Tatami & Kinematics WGSL Render Shader

struct VertexInput {
    @location(0) position: vec3<f32>,
    @location(1) color: vec4<f32>,
    @location(2) normal: vec3<f32>,
};

struct VertexOutput {
    @builtin(position) clip_position: vec4<f32>,
    @location(0) color: vec4<f32>,
    @location(1) world_normal: vec3<f32>,
    @location(2) world_position: vec3<f32>,
};

struct CameraUniform {
    view_proj: mat4x4<f32>,
    camera_pos: vec4<f32>,
};

@group(0) @binding(0) var<uniform> camera: CameraUniform;

@vertex
fn vs_main(in: VertexInput) -> VertexOutput {
    var out: VertexOutput;
    out.clip_position = camera.view_proj * vec4<f32>(in.position, 1.0);
    out.color = in.color;
    out.world_normal = in.normal;
    out.world_position = in.position;
    return out;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
    let light_dir = normalize(vec3<f32>(0.5, 1.0, 0.3));
    let ambient = 0.25;
    let diffuse = max(dot(normalize(in.world_normal), light_dir), 0.0) * 0.75;
    let lit_color = in.color.rgb * (ambient + diffuse);
    
    // Tatami grid line accent
    let grid_x = abs(fract(in.world_position.x) - 0.5);
    let grid_z = abs(fract(in.world_position.z) - 0.5);
    let is_grid = step(grid_x, 0.02) + step(grid_z, 0.02);
    
    let final_rgb = mix(lit_color, vec3<f32>(0.0, 1.0, 0.8), is_grid * 0.3);
    return vec4<f32>(final_rgb, in.color.a);
}
