import imghdr
import click
import zipfile
import json
import logging
import multiprocessing.pool

from pathlib import Path
from atomicwrites import atomic_write

from origami.batch.core.block_processor import BlockProcessor
from origami.core.block import ConcurrentLineDetector


class WarpDetectionProcessor(BlockProcessor):
	def __init__(self, options):
		super().__init__(options)
		self._options = options

	@property
	def processor_name(self):
		return __loader__.name

	def should_process(self, p: Path) -> bool:
		return (imghdr.what(p) is not None) and\
			p.with_suffix(".warped.contours.zip").exists() and\
			not p.with_suffix(".warped.lines.zip").exists()

	def process(self, page_path: Path):
		blocks = self.read_blocks(page_path)

		detector = ConcurrentLineDetector(
			force_parallel_lines=False,
			fringe_limit=self._options["fringe_limit"],
			text_buffer=self._options["text_buffer"])

		block_lines = detector(blocks)

		lines_path = page_path.with_suffix(".warped.lines.zip")
		with atomic_write(lines_path, mode="wb", overwrite=False) as f:

			with zipfile.ZipFile(f, "w", compression=self.compression) as zf:
				info = dict(version=1)
				zf.writestr("meta.json", json.dumps(info))

				for parts, lines in block_lines.items():
					prediction_name = parts[0]
					class_name = parts[1]
					block_id = parts[2]

					for line_id, line in enumerate(lines):
						line_name = "%s/%s/%s/%04d" % (
							prediction_name, class_name, block_id, line_id)
						zf.writestr("%s.json" % line_name, json.dumps(line.info))


@click.command()
@click.option(
	'-f', '--fringe-limit',
	default=0.1,
	type=float,
	help='ignore region fringes above this ratio')
@click.option(
	'-b', '--text-buffer',
	default=15,
	type=int,
	help='text area boundary expansion in pixels')
@click.argument(
	'data_path',
	type=click.Path(exists=True),
	required=True)
@click.option(
	'--name',
	type=str,
	default="",
	help="Only process paths that conform to the given pattern.")
@click.option(
	'--nolock',
	is_flag=True,
	default=False,
	help="Do not lock files while processing. Breaks concurrent batches, "
	"but is necessary on some network file systems.")
def detect_warp(data_path, **kwargs):
	""" Perform warp detection on all document images in DATA_PATH. Needs
	information from contours batch. """
	processor = WarpDetectionProcessor(kwargs)
	processor.traverse(data_path)


if __name__ == "__main__":
	detect_warp()
