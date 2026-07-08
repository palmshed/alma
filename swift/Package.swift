// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Alma",
    platforms: [
        .macOS(.v15),
    ],
    dependencies: [
        .package(url: "https://github.com/gonzalezreal/MarkdownUI", from: "2.2.0"),
    ],
    targets: [
        .executableTarget(
            name: "Alma",
            dependencies: [
                .product(name: "MarkdownUI", package: "MarkdownUI"),
            ],
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
