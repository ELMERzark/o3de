# AzNetworking

## Module Role

`AzNetworking` is O3DE's networking framework layer. It organizes networking into a set of clean layers:

- networking system component and top-level interfaces
- connection layer
- packet layer
- serialization layer
- TCP transport
- UDP transport

If the question is "how is a network interface created," "where do connection objects live," "how are packets serialized," or "where are TCP and UDP implemented," this is the main entry point.

## Key Entry Points

### 1. `AzNetworking::NetworkingSystemComponent`

Source:

- `Code/Framework/AzNetworking/AzNetworking/Framework/NetworkingSystemComponent.h`
- `Code/Framework/AzNetworking/AzNetworking/Framework/NetworkingSystemComponent.cpp`

This is the `INetworking` system component implementation. It is responsible for:

- creating and destroying network interfaces
- maintaining the network interface table
- registering and creating compressors
- owning TCP and UDP worker threads
- advancing networking work during system tick

The header shows that it owns:

- `TcpListenThread`
- `UdpReaderThread`
- `UdpHeartbeatThread`
- a compressor factory map

### 2. `AzNetworkingModule`

Source:

- `Code/Framework/AzNetworking/AzNetworking/AzNetworkingModule.cpp`

This module is straightforward:

- it registers `NetworkingSystemComponent`
- it marks that component as required

## Layer Map

| Directory | Purpose |
| --- | --- |
| `Framework/` | `INetworking`, `INetworkInterface`, system component, compressor interfaces |
| `ConnectionLayer/` | `IConnection`, `IConnectionSet`, listeners, metrics, sequence support |
| `PacketLayer/` | `IPacket` and `IPacketHeader` abstractions |
| `Serialization/` | input and output serializers, delta support, hash support, change tracking, type validation |
| `TcpTransport/` | TCP connections, interfaces, listener thread, socket management, TLS support |
| `UdpTransport/` | UDP connections, reliability queues, fragmentation, packet tracking, DTLS, heartbeat and reader threads |
| `Utilities/` | helper types such as IP address support |

## Core Subsystems

### 1. Framework layer

Read first:

- `Framework/INetworking.h`
- `Framework/INetworkInterface.h`
- `Framework/ICompressor.h`
- `Framework/NetworkingSystemComponent.h`

This is the top-level abstraction layer.

### 2. Connection and packet abstractions

Read first:

- `ConnectionLayer/IConnection.h`
- `ConnectionLayer/IConnectionSet.h`
- `ConnectionLayer/IConnectionListener.h`
- `PacketLayer/IPacket.h`
- `PacketLayer/IPacketHeader.h`

These interfaces define:

- what a connection object looks like
- how network interfaces own sets of connections
- what packet objects must expose

If an AI needs to understand higher-level protocol implementations, it should first understand these contracts.

### 3. Serialization

Read first:

- `Serialization/ISerializer.h`
- `Serialization/NetworkInputSerializer.h`
- `Serialization/NetworkOutputSerializer.h`
- `Serialization/DeltaSerializer.h`
- `Serialization/TrackChangedSerializer.h`

This layer handles how network data is encoded, compared, and incrementally tracked.

### 4. TCP and UDP transport

Read first:

- `TcpTransport/TcpNetworkInterface.h`
- `TcpTransport/TcpConnection.h`
- `UdpTransport/UdpNetworkInterface.h`
- `UdpTransport/UdpConnection.h`
- `UdpTransport/UdpReliableQueue.h`
- `UdpTransport/UdpPacketHeader.h`

A good reading order is:

1. read `*NetworkInterface`
2. then read `*Connection`
3. then read queue, tracker, header, and socket details

## Read These Files First

- `Code/Framework/AzNetworking/AzNetworking/AzNetworkingModule.cpp`
- `Code/Framework/AzNetworking/AzNetworking/Framework/NetworkingSystemComponent.h`
- `Code/Framework/AzNetworking/AzNetworking/Framework/INetworking.h`
- `Code/Framework/AzNetworking/AzNetworking/Framework/INetworkInterface.h`
- `Code/Framework/AzNetworking/AzNetworking/ConnectionLayer/IConnection.h`
- `Code/Framework/AzNetworking/AzNetworking/PacketLayer/IPacket.h`
- `Code/Framework/AzNetworking/AzNetworking/Serialization/ISerializer.h`
- `Code/Framework/AzNetworking/AzNetworking/TcpTransport/TcpNetworkInterface.h`
- `Code/Framework/AzNetworking/AzNetworking/UdpTransport/UdpNetworkInterface.h`

## AI Search Hints

Use these names first:

- `NetworkingSystemComponent`
- `CreateNetworkInterface`
- `IConnection`
- `INetworkInterface`
- `IPacket`
- `NetworkOutputSerializer`
- `UdpReliableQueue`
- `TcpConnection`

## Common Misreads

- `AzNetworking` provides the transport and abstraction stack, not a complete multiplayer gameplay protocol by itself.
- Business message definitions and replication policy are often implemented in higher-level modules or gems.
- If you read only `TcpTransport` or only `UdpTransport`, you can miss the interface contracts above them. Read `Framework/` and `ConnectionLayer/` first.

## Relationship To Other Modules

- `AzNetworking` uses `AzCore` infrastructure such as components, names, console facilities, and containers.
- It is usually a foundation for higher-level multiplayer systems rather than the final gameplay networking layer.
