import logging
import random
import time

import synpp


_GRAPH_CACHE = {}


def _build_random_graph(seed, number_of_stages, max_parents):
	rng = random.Random(seed)
	graph = {}

	for node_id in range(number_of_stages):
		if node_id == 0:
			graph[node_id] = []
			continue

		parent_count = rng.randint(0, min(max_parents, node_id))
		parents = rng.sample(range(node_id), k=parent_count)
		graph[node_id] = sorted(parents)

	return graph


def _get_graph(seed, number_of_stages):
	key = (seed, number_of_stages)
	if key not in _GRAPH_CACHE:
		_GRAPH_CACHE[key] = _build_random_graph(seed, number_of_stages, max_parents=7)
	return _GRAPH_CACHE[key]


class RandomGraphStage:
	def configure(self, context):
		seed = context.config("speed.seed")
		number_of_stages = context.config("speed.number_of_stages")
		node_id = context.config("speed.node_id")

		graph = _get_graph(seed, number_of_stages)
		for parent_id in graph[node_id]:
			context.stage(RandomGraphStage, config={
				"speed.seed": seed,
				"speed.number_of_stages": number_of_stages,
				"speed.node_id": parent_id,
			})

	def execute(self, context):
		# Do nothing
		return None


def run_random_graph_pipeline(seed, number_of_stages):
	_get_graph(seed, number_of_stages)

	definitions = [{
		"descriptor": RandomGraphStage,
		"config": {
			"speed.seed": seed,
			"speed.number_of_stages": number_of_stages,
			"speed.node_id": node_id,
		},
	} for node_id in range(number_of_stages)]

	started_at = time.perf_counter()
	synpp.run(definitions, config={}, working_directory=None)
	return time.perf_counter() - started_at


def test_speed_random_graph_runs_and_logs():
	logger = logging.getLogger("tests.speed")

	elapsed_10 = run_random_graph_pipeline(seed=1997, number_of_stages=10)
	logger.info("Speed test | stages=10 | elapsed=%.3fs", elapsed_10)
	print("Speed test | stages=10 | elapsed=%.3fs" % elapsed_10)

	elapsed_50 = run_random_graph_pipeline(seed=1997, number_of_stages=50)
	logger.info("Speed test | stages=50 | elapsed=%.3fs", elapsed_50)
	print("Speed test | stages=50 | elapsed=%.3fs" % elapsed_50)
	
	elapsed_200 = run_random_graph_pipeline(seed=1997, number_of_stages=200)
	logger.info("Speed test | stages=200 | elapsed=%.3fs", elapsed_200)
	print("Speed test | stages=200 | elapsed=%.3fs" % elapsed_200)

	assert elapsed_10 >= 0.0
	assert elapsed_200 >= 0.0
