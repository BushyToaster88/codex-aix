use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("cargo:rustc-check-cfg=cfg(codex_bazel)");
    println!("cargo:rerun-if-changed=src/grpc");
    #[cfg(target_os = "aix")]
    println!("cargo:rerun-if-env-changed=PROTOC");

    let mut config = tonic_prost_build::Config::new();
    #[cfg(target_os = "aix")]
    config.protoc_executable(
        std::env::var_os("PROTOC")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("/opt/freeware/bin/protoc")),
    );
    #[cfg(not(target_os = "aix"))]
    config.protoc_executable(protoc_bin_vendored::protoc_bin_path()?);
    let proto_files = glob::glob("src/grpc/*.proto")?.collect::<Result<Vec<_>, _>>()?;

    tonic_prost_build::configure()
        .build_client(/*enable*/ true)
        .build_server(/*enable*/ true)
        .compile_with_config(config, &proto_files, &[PathBuf::from("src/grpc")])?;

    Ok(())
}
