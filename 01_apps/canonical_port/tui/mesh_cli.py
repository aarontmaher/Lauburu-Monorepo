import click
from trogon import tui

@tui()
@click.group()
def cli():
    """Lauburu Mesh Network CLI"""
    pass

@cli.command()
@click.option('--node', default='localhost', help='Target DHT Node')
def ping(node):
    """Ping a specific DHT node"""
    click.echo(f"Pinging node {node}...")
    
@cli.command()
@click.option('--peers', default=10, help='Number of peers to bootstrap')
def bootstrap(peers):
    """Bootstrap the DHT network"""
    click.echo(f"Bootstrapping {peers} peers into the mesh...")

if __name__ == '__main__':
    cli()
