// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Alma",
    platforms: [
        .macOS(.v15),
    ],
    targets: [
        .executableTarget(
            name: "Alma",
            resources: [
                .process("Assets.xcassets"),
            ]
        ),
        .testTarget(
            name: "AlmaTests",
            dependencies: ["Alma"]
        ),
    ]
)
