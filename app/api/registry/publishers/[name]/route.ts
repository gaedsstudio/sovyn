import { getPublisher } from "../../../../../lib/registry/registry";
import { publisherResponse } from "../../../../../lib/registry/responses";

type PublisherRouteContext = {
  readonly params: Promise<{
    readonly name: string;
  }>;
};

export async function GET(_request: Request, context: PublisherRouteContext) {
  const { name } = await context.params;
  const publisher = getPublisher(name);
  return Response.json(publisherResponse(publisher), {
    status: publisher === null ? 404 : 200,
  });
}
