"""
Command Line Interface for SignalWatch
"""
import argparse
import json
from pathlib import Path
from config import Config
from core.api_client import CompaniesHouseClient
from core.batch_processor import BatchProcessor
from core.network_scanner import NetworkScanner
from exporters import CSVExporter, JSONExporter, HTMLExporter


def cmd_scan(args):
    """Scan companies for mismatches"""
    print(f"🔍 SignalWatch - Scanning companies...")
    
    # Parse company numbers
    if args.companies:
        company_numbers = [c.strip() for c in args.companies.split(',')]
    elif args.company:
        company_numbers = [args.company]
    else:
        print("Error: No company numbers provided")
        return
    
    print(f"📋 Companies to scan: {len(company_numbers)}")
    
    # Create processor
    processor = BatchProcessor()
    
    # Progress callback
    def show_progress(status):
        if status['status'] == 'processing':
            print(f"  [{status['current']}/{status['total']}] {status['company_number']}")
        elif status['status'] == 'scanning_network':
            print(f"  🕸️  {status['message']}")
    
    # Process companies
    results = processor.process_companies(
        company_numbers=company_numbers,
        scan_network=args.expand_network,
        network_depth=args.max_depth,
        progress_callback=show_progress
    )
    
    # Get summary
    summary = processor.get_processing_summary(results)
    
    print("\n✅ Scan Complete!")
    print(f"   Total companies: {summary['total_companies']}")
    print(f"   Companies with mismatches: {summary['companies_with_mismatches']}")
    print(f"   Total mismatches: {summary['total_mismatches']}")
    
    if results.get('network'):
        net_stats = results['network']['statistics']
        print(f"\n🕸️  Network Analysis:")
        print(f"   Connected companies: {net_stats['total_companies']}")
        print(f"   Unique directors: {net_stats['total_directors']}")
        print(f"   Total connections: {net_stats['total_connections']}")
    
    # Save results
    output_file = Config.DATA_DIR / 'latest_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    # Auto-export if requested
    if args.export:
        print(f"\n📤 Exporting to {args.export}...")
        cmd_export_results(results, args.export)


def cmd_export_results(results, format_type):
    """Export results helper"""
    if format_type == 'csv':
        exporter = CSVExporter()
        file_path = exporter.export_mismatches(results)
        print(f"   CSV: {file_path}")
        
        summary_path = exporter.export_summary(results)
        print(f"   Summary CSV: {summary_path}")
        
        if results.get('network'):
            network_path = exporter.export_network(results['network'])
            print(f"   Network CSV: {network_path}")
    
    elif format_type == 'json':
        exporter = JSONExporter()
        file_path = exporter.export_full_results(results)
        print(f"   JSON: {file_path}")
    
    elif format_type == 'html':
        exporter = HTMLExporter()
        file_path = exporter.export_report(results)
        print(f"   HTML Report: {file_path}")
        
        widget_path = exporter.export_embeddable_widget(results)
        print(f"   Embeddable Widget: {widget_path}")


def cmd_export(args):
    """Export existing results"""
    print(f"📤 Exporting results from {args.results}...")
    
    # Load results
    with open(args.results, 'r') as f:
        results = json.load(f)
    
    cmd_export_results(results, args.format)
    print("✅ Export complete!")


def cmd_resume(args):
    """Resume from checkpoint"""
    print(f"🔄 Resuming from checkpoint: {args.checkpoint_file}")
    
    processor = BatchProcessor()
    
    def show_progress(status):
        if status['status'] == 'processing':
            print(f"  [{status['current']}/{status['total']}] {status['company_number']}")
    
    results = processor.resume_from_checkpoint(
        checkpoint_file=Path(args.checkpoint_file),
        progress_callback=show_progress
    )
    
    print("✅ Processing resumed and completed!")
    print(f"💾 Results saved to checkpoint file")


def cmd_network(args):
    """Scan director network"""
    print(f"🕸️  Scanning director network...")
    
    company_numbers = [c.strip() for c in args.companies.split(',')]
    print(f"📋 Seed companies: {len(company_numbers)}")
    
    scanner = NetworkScanner()
    network = scanner.scan_network(
        seed_companies=company_numbers,
        max_depth=args.max_depth,
        max_companies=args.max_companies
    )
    
    # Print report
    report = scanner.generate_network_report(network)
    print(report)
    
    # Save network data
    output_file = Config.DATA_DIR / 'network_results.json'
    with open(output_file, 'w') as f:
        json.dump(network, f, indent=2)
    
    print(f"\n💾 Network data saved to: {output_file}")


def cmd_search(args):
    """Search for companies"""
    print(f"🔎 Searching for: {args.query}")
    
    client = CompaniesHouseClient()
    results = client.get_company_search(args.query)
    
    print(f"\n📋 Found {len(results)} results:")
    for result in results[:10]:  # Show top 10
        print(f"   {result['company_number']}: {result['title']}")
        if result.get('company_status'):
            print(f"      Status: {result['company_status']}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='SignalWatch - Companies House Analysis Tool'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan companies for mismatches')
    scan_parser.add_argument('--company', help='Single company number to scan')
    scan_parser.add_argument('--companies', help='Comma-separated company numbers')
    scan_parser.add_argument('--expand-network', action='store_true',
                           help='Scan director networks')
    scan_parser.add_argument('--max-depth', type=int, default=2,
                           help='Network scan depth (default: 2)')
    scan_parser.add_argument('--export', choices=['csv', 'json', 'html'],
                           help='Auto-export results')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export existing results')
    export_parser.add_argument('--results', required=True,
                             help='Path to results JSON file')
    export_parser.add_argument('--format', required=True,
                             choices=['csv', 'json', 'html'],
                             help='Export format')
    
    # Resume command
    resume_parser = subparsers.add_parser('resume', help='Resume from checkpoint')
    resume_parser.add_argument('--checkpoint-file', required=True,
                             help='Path to checkpoint file')
    
    # Network command
    network_parser = subparsers.add_parser('network', help='Scan director network')
    network_parser.add_argument('--companies', required=True,
                              help='Comma-separated seed company numbers')
    network_parser.add_argument('--max-depth', type=int, default=2,
                              help='Scan depth (default: 2)')
    network_parser.add_argument('--max-companies', type=int, default=100,
                              help='Maximum companies to scan (default: 100)')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for companies')
    search_parser.add_argument('query', help='Search query')
    
    args = parser.parse_args()
    
    # Ensure config is loaded
    try:
        Config.validate_api_key()
    except ValueError as e:
        print(f"❌ Error: {e}")
        return
    
    # Execute command
    if args.command == 'scan':
        cmd_scan(args)
    elif args.command == 'export':
        cmd_export(args)
    elif args.command == 'resume':
        cmd_resume(args)
    elif args.command == 'network':
        cmd_network(args)
    elif args.command == 'search':
        cmd_search(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
