#!/usr/bin/env python3
"""Entry point for model training CLI."""

import click

from mcli.lib.ui.styling import error, info, success


@click.group(name="mcli-train", help="Model training CLI for MCLI ML system")
def cli():
    """Main CLI group for model training."""


@cli.command(name="model", help="Train a model")
@click.option("--model-type", required=True, help="Type of model to train")
@click.option("--dataset", required=True, help="Path to training dataset")
@click.option("--epochs", default=100, help="Number of training epochs")
@click.option("--batch-size", default=32, help="Batch size for training")
@click.option("--learning-rate", default=0.001, help="Learning rate")
@click.option("--output-dir", help="Directory to save trained model")
def train_model(
    model_type: str,
    dataset: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    output_dir: str,
):
    """Train a model with the specified parameters."""
    info(f"Training {model_type} model")
    info(f"Dataset: {dataset}")
    info(f"Epochs: {epochs}, Batch size: {batch_size}, Learning rate: {learning_rate}")

    # TODO: Implement actual training logic
    error("Model training functionality not yet implemented")


@cli.command(name="resume", help="Resume training from checkpoint")
@click.option("--checkpoint", required=True, help="Path to checkpoint file")
@click.option("--epochs", default=50, help="Additional epochs to train")
def resume_training(checkpoint: str, epochs: int):
    """Resume training from a checkpoint."""
    info(f"Resuming training from: {checkpoint}")
    info(f"Additional epochs: {epochs}")

    # TODO: Implement resume functionality
    error("Resume training not yet implemented")


@cli.command(name="politician-trading", help="Train politician trading prediction model")
@click.option("--output-dir", default="models", help="Directory to save trained model")
def train_politician_trading(output_dir: str):
    """Train the politician trading prediction model."""
    info("Training politician trading prediction model...")

    try:
        # Import the actual training function
        from mcli.ml.training.train_model import train_politician_trading_model

        # Run the training
        metrics = train_politician_trading_model(output_dir)

        if metrics:
            success(f"Training completed! Final loss: {metrics.get('final_loss', 'N/A')}")
        else:
            error("Training failed")
    except ImportError:
        error("Politician trading model training not available")
    except Exception as e:
        error(f"Training failed: {str(e)}")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
