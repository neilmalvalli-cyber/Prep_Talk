export type GlassShape='rounded'|'circle'|'pill'
export default class Container {
 static instances:Container[]
 static waitingForSnapshot:Container[]
 element:HTMLDivElement
 canvas:HTMLCanvasElement
 type:GlassShape
 width:number
 height:number
 borderRadius:number
 gl:WebGLRenderingContext|null
 gl_refs:{gl?:WebGLRenderingContext;texture?:WebGLTexture;positionBuffer?:WebGLBuffer;texcoordBuffer?:WebGLBuffer;scrollYLoc?:WebGLUniformLocation;containerPositionLoc?:WebGLUniformLocation}
 render?:()=>void
 constructor(options?:{type?:GlassShape;borderRadius?:number;tintOpacity?:number})
 init():void
 createElement():void
 setupCanvas():void
 setupShader(image:HTMLCanvasElement):void
 startRenderLoop():void
 getPosition():{x:number;y:number}
 createProgram(gl:WebGLRenderingContext,vertex:string,fragment:string):WebGLProgram|null
}
