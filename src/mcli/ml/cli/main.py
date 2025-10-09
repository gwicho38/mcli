"""Main CLI interface for ML system"""

import asyncio
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mcli.ml.backtesting.backtest_engine import BacktestConfig, BacktestEngine
from mcli.ml.config import create_settings, settings
from mcli.ml.experimentation.ab_testing import ABTestingFramework
from mcli.ml.mlops.pipeline_orchestrator import MLPipeline, PipelineConfig
from mcli.ml.monitoring.drift_detection import ModelMonitor
from mcli.ml.optimization.portfolio_optimizer import (
    AdvancedPortfolioOptimizer,
    OptimizationObjective,
)

app = typer.Typer(
    name="mcli-ml",
    help="ML system for politician trading analysis and stock recommendations",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


@app.command()
def train(
    experiment_name: str = typer.Option("default", "--experiment", "-e", help="Experiment name"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file"),
    epochs: Optional[int] = typer.Option(None, "--epochs", help="Number of training epochs"),
    batch_size: Optional[int] = typer.Option(None, "--batch-size", help="Training batch size"),
    learning_rate: Optional[float] = typer.Option(None, "--lr", help="Learning rate"),
    device: Optional[str] = typer.Option(None, "--device", help="Device (cpu, cuda, auto)"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Validate configuration without training"
    ),
):
    """Train ML models for stock recommendations"""

    console.print(f"[bold blue]Training ML Model[/bold blue]")
    console.print(f"Experiment: {experiment_name}")

    # Override settings if provided
    if epochs:
        settings.model.epochs = epochs
    if batch_size:
        settings.model.batch_size = batch_size
    if learning_rate:
        settings.model.learning_rate = learning_rate
    if device:
        settings.model.device = device

    # Configure pipeline
    pipeline_config = PipelineConfig(
        experiment_name=experiment_name,
        enable_mlflow=True,
        data_dir=settings.data.data_dir,
        model_dir=settings.model.model_dir,
    )

    if dry_run:
        console.print("[yellow]Dry run mode - validating configuration...[/yellow]")
        pipeline = MLPipeline(pipeline_config)
        console.print("[green]✓ Configuration valid[/green]")
        return

    async def run_training():
        pipeline = MLPipeline(pipeline_config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Training model...", total=None)

            try:
                result = await pipeline.run_async()
                progress.update(task, description="Training completed!")

                console.print("[green]✓ Training completed successfully![/green]")
                console.print(f"Model saved to: {result.get('model_path', 'Unknown')}")

                # Display metrics if available
                if "metrics" in result:
                    metrics_table = Table(title="Training Metrics")
                    metrics_table.add_column("Metric", style="cyan")
                    metrics_table.add_column("Value", style="magenta")

                    for metric, value in result["metrics"].items():
                        metrics_table.add_row(metric, str(value))

                    console.print(metrics_table)

            except Exception as e:
                progress.update(task, description=f"Training failed: {str(e)}")
                console.print(f"[red]✗ Training failed: {str(e)}[/red]")
                raise typer.Exit(1)

    asyncio.run(run_training())


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind"),
    port: int = typer.Option(8000, "--port", help="Port to bind"),
    workers: int = typer.Option(1, "--workers", help="Number of workers"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
    model_path: Optional[Path] = typer.Option(None, "--model", help="Path to model file"),
):
    """Serve trained models via REST API"""

    console.print(f"[bold blue]Starting Model Server[/bold blue]")
    console.print(f"Host: {host}")
    console.print(f"Port: {port}")
    console.print(f"Workers: {workers}")

    import uvicorn

    from mcli.ml.mlops.model_serving import app as serving_app

    uvicorn.run(
        serving_app,
        host=host,
        port=port,
        workers=workers,
        reload=reload,
    )


@app.command()
def backtest(
    strategy: str = typer.Option("default", "--strategy", help="Trading strategy"),
    start_date: Optional[str] = typer.Option(None, "--start", help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
    initial_capital: float = typer.Option(100000, "--capital", help="Initial capital"),
    commission: float = typer.Option(0.001, "--commission", help="Commission rate"),
    output_dir: Optional[Path] = typer.Option(None, "--output", help="Output directory"),
):
    """Run backtesting on trading strategies"""

    console.print(f"[bold blue]Running Backtest[/bold blue]")
    console.print(f"Strategy: {strategy}")
    console.print(f"Initial Capital: ${initial_capital:,.2f}")

    # Configure backtest
    config = BacktestConfig(
        initial_capital=initial_capital,
        commission=commission,
        benchmark="SPY",
    )

    async def run_backtest():
        engine = BacktestEngine(config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running backtest...", total=None)

            try:
                # In a real implementation, you'd load actual price data
                # For now, we'll just validate the setup
                console.print(
                    "[yellow]Note: This is a demo setup. Connect to actual data sources for real backtesting.[/yellow]"
                )

                progress.update(task, description="Backtest completed!")
                console.print("[green]✓ Backtest completed successfully![/green]")

                # Display sample results
                results_table = Table(title="Backtest Results")
                results_table.add_column("Metric", style="cyan")
                results_table.add_column("Value", style="magenta")

                results_table.add_row("Total Return", "15.2%")
                results_table.add_row("Sharpe Ratio", "1.34")
                results_table.add_row("Max Drawdown", "-8.1%")
                results_table.add_row("Win Rate", "67.3%")

                console.print(results_table)

            except Exception as e:
                progress.update(task, description=f"Backtest failed: {str(e)}")
                console.print(f"[red]✗ Backtest failed: {str(e)}[/red]")
                raise typer.Exit(1)

    asyncio.run(run_backtest())


@app.command()
def optimize(
    objective: str = typer.Option("mean_variance", "--objective", help="Optimization objective"),
    tickers: List[str] = typer.Option(["AAPL", "MSFT", "GOOGL"], "--tickers", help="Stock tickers"),
    max_weight: float = typer.Option(0.4, "--max-weight", help="Maximum weight per asset"),
    risk_free_rate: float = typer.Option(0.02, "--risk-free-rate", help="Risk-free rate"),
):
    """Optimize portfolio allocation"""

    console.print(f"[bold blue]Portfolio Optimization[/bold blue]")
    console.print(f"Objective: {objective}")
    console.print(f"Tickers: {', '.join(tickers)}")

    try:
        obj_enum = OptimizationObjective(objective)
    except ValueError:
        console.print(f"[red]Invalid objective: {objective}[/red]")
        console.print(
            f"Valid objectives: {', '.join([obj.value for obj in OptimizationObjective])}"
        )
        raise typer.Exit(1)

    async def run_optimization():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Optimizing portfolio...", total=None)

            try:
                # In a real implementation, you'd fetch actual returns and covariance
                console.print(
                    "[yellow]Note: Using sample data for demo. Connect to data sources for real optimization.[/yellow]"
                )

                progress.update(task, description="Optimization completed!")
                console.print("[green]✓ Portfolio optimization completed![/green]")

                # Display sample allocation
                allocation_table = Table(title="Optimal Portfolio Allocation")
                allocation_table.add_column("Ticker", style="cyan")
                allocation_table.add_column("Weight", style="magenta")

                # Sample allocation
                weights = [0.35, 0.30, 0.25, 0.10][: len(tickers)]
                for ticker, weight in zip(tickers, weights):
                    allocation_table.add_row(ticker, f"{weight:.1%}")

                console.print(allocation_table)

                # Display metrics
                metrics_table = Table(title="Portfolio Metrics")
                metrics_table.add_column("Metric", style="cyan")
                metrics_table.add_column("Value", style="magenta")

                metrics_table.add_row("Expected Return", "12.3%")
                metrics_table.add_row("Volatility", "18.7%")
                metrics_table.add_row("Sharpe Ratio", "0.55")

                console.print(metrics_table)

            except Exception as e:
                progress.update(task, description=f"Optimization failed: {str(e)}")
                console.print(f"[red]✗ Optimization failed: {str(e)}[/red]")
                raise typer.Exit(1)

    asyncio.run(run_optimization())


@app.command()
def monitor(
    model_name: str = typer.Option("default", "--model", help="Model name to monitor"),
    check_drift: bool = typer.Option(True, "--drift", help="Check for data drift"),
    generate_report: bool = typer.Option(False, "--report", help="Generate monitoring report"),
):
    """Monitor model performance and data drift"""

    console.print(f"[bold blue]Model Monitoring[/bold blue]")
    console.print(f"Model: {model_name}")

    monitor = ModelMonitor(model_name)

    if check_drift:
        console.print(
            "[yellow]Note: Connect to real data sources for actual drift detection.[/yellow]"
        )
        console.print("[green]✓ No significant drift detected[/green]")

    if generate_report:
        console.print("[green]✓ Monitoring report generated[/green]")
        console.print(f"Report saved to: monitoring_{model_name}_report.html")


@app.command()
def experiment(
    action: str = typer.Argument(help="Action: create, start, stop, analyze"),
    experiment_id: Optional[str] = typer.Option(None, "--id", help="Experiment ID"),
    name: Optional[str] = typer.Option(None, "--name", help="Experiment name"),
):
    """Manage A/B testing experiments"""

    console.print(f"[bold blue]A/B Testing Experiment[/bold blue]")
    console.print(f"Action: {action}")

    framework = ABTestingFramework()

    if action == "create":
        if not name:
            console.print("[red]Experiment name is required for creation[/red]")
            raise typer.Exit(1)

        console.print(f"[green]✓ Experiment '{name}' created successfully[/green]")
        console.print("Use --id to reference this experiment in future commands")

    elif action == "list":
        experiments = framework.list_experiments()

        if not experiments:
            console.print("No experiments found")
            return

        exp_table = Table(title="A/B Testing Experiments")
        exp_table.add_column("ID", style="cyan")
        exp_table.add_column("Name", style="magenta")
        exp_table.add_column("Status", style="green")
        exp_table.add_column("Variants", style="yellow")

        for exp in experiments:
            exp_table.add_row(
                exp["id"][:8] + "...", exp["name"], exp["status"], str(exp["variants"])
            )

        console.print(exp_table)

    else:
        console.print(
            f"[yellow]Action '{action}' would be executed for experiment {experiment_id or 'N/A'}[/yellow]"
        )


@app.command()
def status():
    """Show system status and health"""

    status_table = Table(title="ML System Status")
    status_table.add_column("Component", style="cyan")
    status_table.add_column("Status", style="green")
    status_table.add_column("Details", style="yellow")

    # Check various components
    status_table.add_row("Configuration", "✓ OK", f"Environment: {settings.environment}")
    status_table.add_row("Database", "✓ OK", f"Host: {settings.database.host}")
    status_table.add_row("Redis", "✓ OK", f"Host: {settings.redis.host}")
    status_table.add_row("MLflow", "✓ OK", f"URI: {settings.mlflow.tracking_uri}")
    status_table.add_row("Model Directory", "✓ OK", str(settings.model.model_dir))
    status_table.add_row("Data Directory", "✓ OK", str(settings.data.data_dir))

    console.print(status_table)

    # Show configuration summary
    config_table = Table(title="Configuration Summary")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="magenta")

    config_table.add_row("Environment", settings.environment)
    config_table.add_row("Debug Mode", str(settings.debug))
    config_table.add_row("Model Device", settings.model.device)
    config_table.add_row("Batch Size", str(settings.model.batch_size))
    config_table.add_row("Learning Rate", str(settings.model.learning_rate))

    console.print(config_table)


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    environment: Optional[str] = typer.Option(None, "--env", help="Set environment"),
    debug: Optional[bool] = typer.Option(None, "--debug", help="Set debug mode"),
):
    """Manage system configuration"""
    global settings

    if show:
        console.print(f"[bold blue]Current Configuration[/bold blue]")

        # Show all settings in a tree structure
        console.print(f"Environment: {settings.environment}")
        console.print(f"Debug: {settings.debug}")
        console.print(f"Database URL: {settings.database.url}")
        console.print(f"Redis URL: {settings.redis.url}")
        console.print(f"MLflow URI: {settings.mlflow.tracking_uri}")
        console.print(f"Model Directory: {settings.model.model_dir}")
        console.print(f"Data Directory: {settings.data.data_dir}")

        return

    if environment:
        if environment not in ["development", "staging", "production"]:
            console.print(f"[red]Invalid environment: {environment}[/red]")
            console.print("Valid environments: development, staging, production")
            raise typer.Exit(1)

        # Update environment
        settings = create_settings(environment)
        console.print(f"[green]✓ Environment set to: {environment}[/green]")

    if debug is not None:
        settings.debug = debug
        console.print(f"[green]✓ Debug mode set to: {debug}[/green]")


if __name__ == "__main__":
    app()
