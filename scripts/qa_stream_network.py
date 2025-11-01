#!/usr/bin/env python3
"""
Quality assurance report generator for DEM-derived stream networks.

Generates comprehensive statistics and markdown report including:
- Stream count and length by stream order
- Drainage area distribution
- Confidence score distribution
- Flow persistence classification
- Geometric metrics (sinuosity)
- Spatial coverage analysis

Usage:
    python scripts/qa_stream_network.py \
      --input data/processed/streams_filtered.gpkg \
      --layer streams_t100_filtered \
      --output reports/stream_qa_report.md
"""

import click
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
from datetime import datetime


@click.command()
@click.option(
    '--input', '-i',
    type=click.Path(exists=True),
    required=True,
    help='Input streams GeoPackage'
)
@click.option(
    '--layer', '-l',
    type=str,
    default='streams_t100_filtered',
    help='Layer name (default: streams_t100_filtered)'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    default='reports/stream_qa_report.md',
    help='Output markdown report path'
)
def main(input, layer, output):
    """Generate QA report for DEM-derived stream network."""

    input_path = Path(input)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"Generating QA report for: {input_path} (layer: {layer})")

    # Load streams
    try:
        streams_gdf = gpd.read_file(input_path, layer=layer)
    except Exception as e:
        click.echo(f"Error loading layer: {e}")
        return 1

    click.echo(f"  Loaded {len(streams_gdf)} stream features")

    # Generate report
    report = generate_qa_report(streams_gdf, input_path, layer)

    # Write to file
    with open(output_path, 'w') as f:
        f.write(report)

    click.echo(f"\nReport saved to: {output_path}")

    # Also print summary to console
    print_summary(streams_gdf)


def generate_qa_report(streams_gdf, input_path, layer_name):
    """Generate comprehensive markdown QA report."""

    report_lines = []

    # Header
    report_lines.append("# Stream Network Quality Assurance Report")
    report_lines.append("")
    report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**Source:** `{input_path}` (layer: `{layer_name}`)")
    report_lines.append(f"**CRS:** {streams_gdf.crs}")
    report_lines.append("")

    # Overall Statistics
    report_lines.append("## Overall Statistics")
    report_lines.append("")
    total_count = len(streams_gdf)
    total_length_km = streams_gdf['length_km'].sum()
    total_length_mi = total_length_km * 0.621371

    bounds = streams_gdf.total_bounds
    report_lines.append(f"- **Total stream segments:** {total_count:,}")
    report_lines.append(f"- **Total stream length:** {total_length_km:.2f} km ({total_length_mi:.2f} mi)")
    report_lines.append(f"- **Average segment length:** {streams_gdf['length_m'].mean():.1f} m")
    report_lines.append(f"- **Median segment length:** {streams_gdf['length_m'].median():.1f} m")
    report_lines.append(f"- **Spatial extent:** {bounds[0]:.4f}, {bounds[1]:.4f} to {bounds[2]:.4f}, {bounds[3]:.4f}")
    report_lines.append("")

    # Stream Order Distribution
    if 'order' in streams_gdf.columns:
        report_lines.append("## Stream Order Distribution")
        report_lines.append("")
        report_lines.append("| Order | Count | % of Total | Total Length (km) | % of Length |")
        report_lines.append("|-------|-------|------------|-------------------|-------------|")

        for order in sorted(streams_gdf['order'].unique()):
            order_streams = streams_gdf[streams_gdf['order'] == order]
            count = len(order_streams)
            count_pct = (count / total_count) * 100
            length_km = order_streams['length_km'].sum()
            length_pct = (length_km / total_length_km) * 100
            report_lines.append(f"| {int(order)} | {count:,} | {count_pct:.1f}% | {length_km:.2f} | {length_pct:.1f}% |")

        report_lines.append("")

    # Drainage Area Distribution
    if 'drainage_area_sqkm' in streams_gdf.columns:
        report_lines.append("## Drainage Area Distribution")
        report_lines.append("")

        da_valid = streams_gdf[streams_gdf['drainage_area_sqkm'].notna()]['drainage_area_sqkm']

        if len(da_valid) > 0:
            report_lines.append(f"- **Streams with drainage area data:** {len(da_valid)} ({len(da_valid)/total_count*100:.1f}%)")
            report_lines.append(f"- **Mean drainage area:** {da_valid.mean():.3f} km²")
            report_lines.append(f"- **Median drainage area:** {da_valid.median():.3f} km²")
            report_lines.append(f"- **Min drainage area:** {da_valid.min():.3f} km²")
            report_lines.append(f"- **Max drainage area:** {da_valid.max():.3f} km²")
            report_lines.append("")

            # Histogram
            report_lines.append("### Drainage Area Histogram")
            report_lines.append("")
            report_lines.append("| Range (km²) | Count | % of Total |")
            report_lines.append("|-------------|-------|------------|")

            bins = [0, 0.1, 0.5, 1.0, 5.0, 10.0, float('inf')]
            labels = ['<0.1', '0.1-0.5', '0.5-1.0', '1.0-5.0', '5.0-10.0', '>10.0']

            for i, label in enumerate(labels):
                count = ((da_valid >= bins[i]) & (da_valid < bins[i+1])).sum()
                pct = (count / len(da_valid)) * 100
                report_lines.append(f"| {label} | {count:,} | {pct:.1f}% |")

            report_lines.append("")

    # Flow Persistence Classification
    if 'stream_type' in streams_gdf.columns:
        report_lines.append("## Flow Persistence Classification")
        report_lines.append("")
        report_lines.append("| Stream Type | Count | % of Total | Total Length (km) | % of Length |")
        report_lines.append("|-------------|-------|------------|-------------------|-------------|")

        for stype in ['Perennial', 'Intermittent', 'Ephemeral']:
            stype_streams = streams_gdf[streams_gdf['stream_type'] == stype]
            count = len(stype_streams)
            count_pct = (count / total_count) * 100 if total_count > 0 else 0
            length_km = stype_streams['length_km'].sum()
            length_pct = (length_km / total_length_km) * 100 if total_length_km > 0 else 0
            report_lines.append(f"| {stype} | {count:,} | {count_pct:.1f}% | {length_km:.2f} | {length_pct:.1f}% |")

        report_lines.append("")

    # Confidence Score Distribution
    if 'confidence_score' in streams_gdf.columns:
        report_lines.append("## Confidence Score Distribution")
        report_lines.append("")

        conf_scores = streams_gdf['confidence_score']
        report_lines.append(f"- **Mean confidence:** {conf_scores.mean():.3f}")
        report_lines.append(f"- **Median confidence:** {conf_scores.median():.3f}")
        report_lines.append(f"- **Min confidence:** {conf_scores.min():.3f}")
        report_lines.append(f"- **Max confidence:** {conf_scores.max():.3f}")
        report_lines.append("")

        # Histogram
        report_lines.append("| Confidence Range | Count | % of Total | Description |")
        report_lines.append("|------------------|-------|------------|-------------|")

        bins = [(0, 0.3, 'Low'), (0.3, 0.5, 'Medium'), (0.5, 0.7, 'High'), (0.7, 1.0, 'Very High')]
        for min_val, max_val, label in bins:
            count = ((conf_scores >= min_val) & (conf_scores < max_val)).sum()
            pct = (count / total_count) * 100
            report_lines.append(f"| {min_val:.1f} - {max_val:.1f} | {count:,} | {pct:.1f}% | {label} |")

        report_lines.append("")

        # Low confidence streams analysis
        low_conf = streams_gdf[conf_scores < 0.3]
        if len(low_conf) > 0:
            report_lines.append(f"**Note:** {len(low_conf)} streams ({len(low_conf)/total_count*100:.1f}%) have low confidence scores (<0.3).")
            report_lines.append("These may be DEM artifacts and should be visually inspected.")
            report_lines.append("")

    # Geometric Metrics
    if 'sinuosity' in streams_gdf.columns:
        report_lines.append("## Geometric Metrics")
        report_lines.append("")

        sinuosity = streams_gdf['sinuosity']
        report_lines.append(f"- **Mean sinuosity:** {sinuosity.mean():.3f}")
        report_lines.append(f"- **Median sinuosity:** {sinuosity.median():.3f}")
        report_lines.append("")

        # Very straight streams (potential artifacts)
        very_straight = streams_gdf[sinuosity < 1.1]
        if len(very_straight) > 0:
            report_lines.append(f"**Warning:** {len(very_straight)} streams ({len(very_straight)/total_count*100:.1f}%) are very straight (sinuosity < 1.1).")
            report_lines.append("These may be DEM artifacts or channelized streams. Recommend visual inspection.")
            report_lines.append("")

    # Data Quality Checks
    report_lines.append("## Data Quality Checks")
    report_lines.append("")

    # Check for null geometries
    null_geom = streams_gdf.geometry.isna().sum()
    report_lines.append(f"- **Null geometries:** {null_geom} ({null_geom/total_count*100:.1f}%)")

    # Check for null drainage areas
    if 'drainage_area_sqkm' in streams_gdf.columns:
        null_da = streams_gdf['drainage_area_sqkm'].isna().sum()
        report_lines.append(f"- **Missing drainage area:** {null_da} ({null_da/total_count*100:.1f}%)")

    # Check for null stream types
    if 'stream_type' in streams_gdf.columns:
        null_type = streams_gdf['stream_type'].isna().sum()
        report_lines.append(f"- **Missing stream type:** {null_type} ({null_type/total_count*100:.1f}%)")

    report_lines.append("")

    # Recommendations
    report_lines.append("## Recommendations")
    report_lines.append("")

    # Based on confidence scores
    if 'confidence_score' in streams_gdf.columns:
        low_conf_pct = (conf_scores < 0.3).sum() / total_count * 100
        if low_conf_pct > 10:
            report_lines.append(f"1. **High artifact rate:** {low_conf_pct:.1f}% of streams have low confidence. Consider:")
            report_lines.append("   - Increasing `--min-length` parameter")
            report_lines.append("   - Increasing `--min-drainage-area` parameter")
            report_lines.append("   - Using a coarser threshold (t250 or t500)")
        elif low_conf_pct < 5:
            report_lines.append(f"1. **Good filtering:** Only {low_conf_pct:.1f}% low-confidence streams detected.")

    # Based on drainage area coverage
    if 'drainage_area_sqkm' in streams_gdf.columns:
        da_coverage = (streams_gdf['drainage_area_sqkm'].notna().sum() / total_count) * 100
        if da_coverage < 95:
            report_lines.append(f"2. **Drainage area coverage:** Only {da_coverage:.1f}% of streams have drainage area data.")
            report_lines.append("   - Ensure `--flow-acc` parameter is provided to filter_dem_streams.py")

    report_lines.append("")
    report_lines.append("---")
    report_lines.append("*Generated by qa_stream_network.py*")

    return "\n".join(report_lines)


def print_summary(streams_gdf):
    """Print quick summary to console."""

    click.echo("\n" + "="*60)
    click.echo("SUMMARY")
    click.echo("="*60)

    click.echo(f"Total streams: {len(streams_gdf):,}")
    click.echo(f"Total length: {streams_gdf['length_km'].sum():.2f} km")

    if 'confidence_score' in streams_gdf.columns:
        mean_conf = streams_gdf['confidence_score'].mean()
        low_conf_count = (streams_gdf['confidence_score'] < 0.3).sum()
        click.echo(f"Mean confidence: {mean_conf:.3f}")
        click.echo(f"Low confidence streams: {low_conf_count} ({low_conf_count/len(streams_gdf)*100:.1f}%)")

    if 'stream_type' in streams_gdf.columns:
        click.echo("\nFlow persistence:")
        for stype in ['Perennial', 'Intermittent', 'Ephemeral']:
            count = (streams_gdf['stream_type'] == stype).sum()
            click.echo(f"  {stype}: {count} ({count/len(streams_gdf)*100:.1f}%)")

    click.echo("="*60)


if __name__ == '__main__':
    main()
